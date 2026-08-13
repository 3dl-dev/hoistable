#!/usr/bin/env python3
"""Where a hoist runs: the isolation substrate, resolved not depended on.

The envelope grades; it does not care *where* the config's steps execute. That
"where" is a resolved bind, exactly the verb the rest of Hoistable already runs on
(a config ref resolves path->index->URL, operators resolve pin->local, a secret
resolves on the target). Isolation is the same: the config names the strength it
needs, and sysop resolves the strongest rung the target actually offers.

A substrate is a small contract, three verbs and a place to work:

    provision()  ->  stand up a throwaway place to run (or nothing, for the host).
    exec(cmd)    ->  run one shell step there, return (rc, tail).
    teardown()   ->  destroy it; a hoist leaves the target as it found it.
    workroot     ->  the base dir a clone/deploy happens under, in that place.

The host is itself the floor substrate: its exec is a plain subprocess, its
provision and teardown are no-ops, and its strength is "host" (a namespace on the
same machine, so a deploy that ignores its own isolation can still reach host
state). A stronger rung (dind here; a burnable VM or a k3s Job next) runs the
config's steps somewhere a deploy *cannot* reach host state, whatever the config
declares. Which rung you get is resolved, and the guarantee is only as strong as
the rung that answered -- reported honestly, never assumed.

The ladder below is illustrative, not a closed set. A new rung is a new adapter
(build-rule 2), and the knowledge of how to drive it (dind's privileged daemon,
kubectl exec, ssh) lives in the adapter, not in the grader (build-rule 6, point
don't embed).

Standard library only. Docker is not imported or required; the dind rung shells
out to it and simply does not resolve on a target without it -- which is the whole
point: a missing substrate is an unresolved bind, reported at the door, not a hard
dependency of this module.
"""

import os
import shlex
import subprocess
import time
import uuid


# Strength ordering. A config asks for at least one of these; the resolver returns
# a rung that meets or exceeds it, or reports cannot-build if none does.
STRENGTHS = {"host": 0, "environmental": 1}


def _sh(cmd, timeout, env=None):
    """Run a shell command on the host, return (rc, tail). The one place this
    module touches the host directly: to drive a substrate's own tooling."""
    try:
        p = subprocess.run(cmd, shell=True, timeout=timeout,
                           capture_output=True, text=True, env=env)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()[-2000:]
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 127, f"could not run: {e}"


class Substrate:
    """The contract. A rung implements provision/exec/teardown and names its
    strength and workroot."""

    name = "base"
    strength = "host"

    def workroot(self):
        raise NotImplementedError

    def stage(self, local_path):
        """Make a host-local source path reachable from inside the substrate,
        returning the path to clone *from* there. The host returns it unchanged;
        a remote substrate mounts or copies it in."""
        return local_path

    def provision(self):
        return True, ""

    def exec(self, cmd, cwd, env_overrides, timeout):
        raise NotImplementedError

    def teardown(self):
        return True, ""

    def residue(self):
        """Host resources still attributable to THIS substrate after teardown: the
        environmental blast radius, checked by our own footprint rather than by a
        full host-daemon diff. A full diff is unreliable on a shared host (unrelated
        containers churn on their own), and it over-claims; scoping to our named
        resources verifies the honest guarantee -- the hoist added exactly its
        substrate and reclaimed exactly its substrate -- and is immune to that
        churn. Empty list means clean. The host floor owns nothing to reclaim."""
        return []


class HostSubstrate(Substrate):
    """The floor rung: run on this machine. Strength 'host' -- isolation is only
    as strong as the config's own declared namespace, so a deploy that ignores it
    can reach host state. This is exactly today's behavior, kept identical so the
    existing envelope tests are unchanged."""

    name = "host"
    strength = "host"

    def __init__(self, target_dir):
        self.target_dir = target_dir

    def workroot(self):
        return self.target_dir

    def exec(self, cmd, cwd, env_overrides, timeout):
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (env_overrides or {}).items()})
        try:
            p = subprocess.run(cmd, shell=True, cwd=cwd, timeout=timeout,
                               capture_output=True, text=True, env=env)
            out = (p.stdout or "") + (p.stderr or "")
            return p.returncode, out.strip()[-2000:]
        except subprocess.TimeoutExpired:
            return 124, f"timed out after {timeout}s"
        except Exception as e:  # noqa: BLE001
            return 127, f"could not run: {e}"


class DindSubstrate(Substrate):
    """The first environmental rung: a throwaway Docker-in-Docker container with
    its own inner daemon. The config's steps run inside it, so a deploy physically
    cannot touch host state: a file it writes lands in the container filesystem, a
    container it starts (or removes) lives on the inner daemon the host never sees.
    Teardown is 'docker rm -f' on the one outer container, which reclaims every
    inner container, volume, and network with it.

    The host guarantee is checked at host level: 'docker ps -a' etc. on the host
    daemon is snapshotted before provision and after teardown and must be identical.

    This adapter is the authority on dind, not the grader. A target without docker,
    or where a privileged container will not start, simply fails to resolve here --
    an honest unresolved bind, not a crash."""

    name = "dind"
    strength = "environmental"
    IMAGE = "docker:27-dind"
    # Tools the app steps expect inside the substrate. dind is alpine; the base
    # image carries docker+compose+git but not python/openssl, so add them.
    PREPARE = ("apk add --no-cache python3 py3-pip openssl curl bash git "
               ">/dev/null 2>&1 || true; mkdir -p /work")

    def __init__(self, app="app", source_local=None):
        self.cid = f"hoist-sbx-{app}-{uuid.uuid4().hex[:8]}"
        self.source_local = source_local
        self._staged = None
        self.provisioned = False

    def workroot(self):
        return "/work"

    def stage(self, local_path):
        # The source is mounted read-only at provision; return its in-container
        # path so the clone reads from the mount, not a host path that does not
        # exist inside. Read-only: the source is not host *state* we can mutate.
        if self._staged and local_path == self.source_local:
            return self._staged
        return local_path

    def provision(self):
        mount = ""
        if self.source_local and os.path.isdir(self.source_local):
            self._staged = "/staged-src"
            mount = f"-v {shlex.quote(os.path.abspath(self.source_local))}:/staged-src:ro"
        # Non-TLS so the inner client talks to the inner daemon over the default
        # socket without cert wrangling.
        rc, tail = _sh(
            f"docker run -d --privileged -e DOCKER_TLS_CERTDIR= {mount} "
            f"--name {shlex.quote(self.cid)} {self.IMAGE}",
            timeout=120)
        if rc != 0:
            return False, f"could not start dind container: {tail}"
        self.provisioned = True
        # Wait for the inner daemon to answer.
        deadline = 60
        waited = 0
        while waited < deadline:
            rc, _ = _sh(f"docker exec {shlex.quote(self.cid)} docker info "
                        f">/dev/null 2>&1", timeout=20)
            if rc == 0:
                break
            waited += 3
            time.sleep(3)
        else:
            return False, "inner docker daemon did not come up within 60s"
        rc, tail = _sh(f"docker exec {shlex.quote(self.cid)} sh -lc "
                       f"{shlex.quote(self.PREPARE)}", timeout=180)
        if rc != 0:
            return False, f"could not prepare dind tools: {tail}"
        return True, self.cid

    def exec(self, cmd, cwd, env_overrides, timeout):
        env_flags = " ".join(
            f"-e {shlex.quote(f'{k}={v}')}" for k, v in (env_overrides or {}).items())
        full = (f"docker exec -w {shlex.quote(cwd)} {env_flags} "
                f"{shlex.quote(self.cid)} sh -lc {shlex.quote(cmd)}")
        return _sh(full, timeout=timeout)

    def teardown(self):
        if not self.provisioned:
            return True, ""
        # -v removes the anonymous volume dind declares for /var/lib/docker, so the
        # host's 'docker volume ls' is left byte-identical: teardown nets to zero.
        rc, tail = _sh(f"docker rm -fv {shlex.quote(self.cid)}", timeout=60)
        return rc == 0, tail

    def residue(self):
        # Our footprint on the host is exactly one named container (its anonymous
        # volume goes with it on 'docker rm -fv'). After teardown, that container
        # must be gone. Scoped to our own name, so unrelated containers churning on
        # a shared host do not register as a false violation.
        rc, out = _sh(f"docker ps -aq --filter name={shlex.quote(self.cid)}",
                     timeout=30)
        return [l for l in out.splitlines() if l.strip()] if rc == 0 else []


# --- the ladder ----------------------------------------------------------------
# A rung is (name, strength, host-prereq probe, factory). The resolver tries them
# in order and binds the first whose prereq passes. Order is illustrative; adding
# podman / user-ns / a burnable VM / a k3s Job is adding a rung here, never a fork
# of the grader.

def _dind_factory(config, target_dir):
    src = (config.get("source") or {}).get("clone")
    src_local = src if src and os.path.isdir(src) else None
    return DindSubstrate(app=config.get("app", "app"), source_local=src_local)


ENVIRONMENTAL_LADDER = [
    ("dind", "environmental",
     "docker version >/dev/null 2>&1", _dind_factory),
    # next rungs (probes real, adapters unbuilt -- left out of the resolvable set
    # on purpose, so the resolver never claims a capability it cannot drive):
    #   ("podman-rootless", "environmental", "podman info ...", _podman_factory)
    #   ("k3s-job",         "environmental", "kubectl get ns ...", _k3s_factory)
    #   ("burnable-vm",     "environmental", "<cloud probe>",     _vm_factory)
]


def resolve_substrate(config, profile, target_dir, timeout=60, log=lambda m: None):
    """Resolve the substrate a hoist will run in, first-match down the ladder.

    Returns (substrate, info) on success, or (None, reason) for a cannot-build.
    `info` records what resolved and how strong it is, for the report.

    Strength is taken from the profile's isolation block: require='environmental'
    means the host floor is not good enough and an environmental rung must resolve.
    Default (require absent or 'namespace'/'host') uses the host substrate, which is
    today's behavior: the config's own declared namespace isolation, no stronger.
    """
    iso = profile.get("isolation") or {}
    require = iso.get("require", "host")
    if require in ("namespace", None):
        require = "host"
    if require not in STRENGTHS:
        return None, f"unknown isolation strength required: {require!r}"

    if STRENGTHS[require] <= STRENGTHS["host"]:
        return HostSubstrate(target_dir), {"name": "host", "strength": "host",
                                           "required": require}

    # An environmental (or stronger) rung is required. Try the ladder.
    tried = []
    order = iso.get("substrates")  # optional explicit preference order by name
    ladder = ENVIRONMENTAL_LADDER
    if order:
        by_name = {r[0]: r for r in ENVIRONMENTAL_LADDER}
        ladder = [by_name[n] for n in order if n in by_name]
    for name, strength, prereq, factory in ladder:
        if STRENGTHS[strength] < STRENGTHS[require]:
            continue
        rc, _ = _sh(prereq, timeout=timeout)
        if rc != 0:
            tried.append(f"{name}(prereq absent)")
            continue
        sub = factory(config, target_dir)
        log(f"resolving isolation substrate: {name} (strength {strength})")
        ok, detail = sub.provision()
        if not ok:
            tried.append(f"{name}({detail})")
            sub.teardown()
            continue
        return sub, {"name": name, "strength": strength, "required": require,
                    "handle": detail}
    return None, ("no isolation substrate resolved on this target for required "
                  f"strength {require!r}; tried: {', '.join(tried) or '(none)'}")


def probe_manifest(timeout=30):
    """The capability manifest: which isolation rungs this target offers RIGHT
    NOW, re-derived by probing. The host floor is always present; each
    environmental rung is available iff its host prerequisite answers. This is the
    thing a saved resolution snapshots as a hint and a replay RE-PROBES rather than
    trusts (continuation identity: the environment is re-derived, never remembered).
    """
    manifest = [{"name": "host", "strength": "host", "available": True}]
    for name, strength, prereq, _factory in ENVIRONMENTAL_LADDER:
        rc, _ = _sh(prereq, timeout=timeout)
        manifest.append({"name": name, "strength": strength, "available": rc == 0})
    return manifest


def choose_from_manifest(manifest, require="host"):
    """Given a manifest and a required strength, the rung a resolution would pick:
    the first available rung that meets or exceeds the strength. None if nothing
    on the target meets it now (an honest cannot-build on replay)."""
    if require in ("namespace", None):
        require = "host"
    need = STRENGTHS.get(require)
    if need is None:
        return None
    for rung in manifest:
        if rung.get("available") and STRENGTHS.get(rung["strength"], -1) >= need:
            return {"name": rung["name"], "strength": rung["strength"]}
    return None


def probe_substrate(config, profile, timeout=60):
    """The know-early pass for isolation: would a substrate resolve, without
    provisioning anything? preflight must touch nothing, so it probes each rung's
    host prerequisite and reports feasibility, deploying no container or VM.

    Returns (feasible, info-or-reason). The host floor is always feasible; an
    environmental requirement is feasible iff some rung's prereq probe passes."""
    iso = profile.get("isolation") or {}
    require = iso.get("require", "host")
    if require in ("namespace", None):
        require = "host"
    if require not in STRENGTHS:
        return False, f"unknown isolation strength required: {require!r}"
    if STRENGTHS[require] <= STRENGTHS["host"]:
        return True, {"name": "host", "strength": "host", "required": require,
                     "would_resolve": True}
    order = iso.get("substrates")
    ladder = ENVIRONMENTAL_LADDER
    if order:
        by_name = {r[0]: r for r in ENVIRONMENTAL_LADDER}
        ladder = [by_name[n] for n in order if n in by_name]
    tried = []
    for name, strength, prereq, _factory in ladder:
        if STRENGTHS[strength] < STRENGTHS[require]:
            continue
        rc, _ = _sh(prereq, timeout=timeout)
        if rc == 0:
            return True, {"name": name, "strength": strength, "required": require,
                         "would_resolve": True}
        tried.append(f"{name}(prereq absent)")
    return False, ("no isolation substrate would resolve for required strength "
                   f"{require!r}; tried: {', '.join(tried) or '(none)'}")
