#!/usr/bin/env python3
"""Hoistable's honest-grade envelope runner.

The neutral core of build-rule 7 ("no silent success"). It takes a Layer 2
config, hoists the app onto a target the way the config says to, and grades the
result honestly. It never claims a success it did not earn.

The shape is skillc's envelope applied to a deployable system instead of a voice:

  - binds        the local capabilities the config requires (docker, a secret).
                 A missing required bind is a CANNOT-BUILD: named, and we stop.
  - substrate    WHERE the config's steps run, resolved not depended on. The host
                 is the floor rung; a config that needs a deploy to be unable to
                 touch host state asks for an environmental rung (dind here), and
                 the runner resolves the strongest the target offers or reports
                 cannot-build. See substrate.py.
  - preflight    cheap probes run before deploy, so the user learns at the door.
                 A required preflight blocker is also a CANNOT-BUILD.
  - bringup      clone + configure + deploy the chosen profile. The install gate.
  - health       is the system actually up. Counted N of M.
  - acceptance   the held-back checks. Their pass fraction is the honest transfer
                 score: whether the app really works here, not just came up.

Three plain outcomes, exactly as skillc reports:
  - built           install gate up and every acceptance check passed.
  - honest-failure  it came up but something did not transfer; we say what.
  - cannot-build    a required bind, preflight blocker, or isolation substrate is
                    missing, named.

Standard library only (build-rule 3). The config is data; this runner is generic.
App specifics live in the config, never here (build-rule 6, point don't embed).
The "where it runs" is a resolved bind (substrate.py), not a hardcoded backend.
"""

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import uuid

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import substrate  # noqa: E402


DEFAULT_TIMEOUT = 600


def _run(cmd, cwd, timeout=DEFAULT_TIMEOUT, env=None):
    """Run a shell command on the host, return (rc, tail-of-output). Used for the
    host-side binds gate; every step that runs *in the substrate* goes through the
    resolved substrate's exec instead."""
    try:
        p = subprocess.run(
            cmd, shell=True, cwd=cwd, timeout=timeout,
            capture_output=True, text=True, env=env,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()[-2000:]
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except Exception as e:  # noqa: BLE001 - report any launch failure honestly
        return 127, f"could not run: {e}"


def _step_list(profile, key):
    return profile.get(key, []) or []


def _free_port():
    """Ask the OS for an unused host port so an isolated hoist never fights an
    existing instance for a fixed port."""
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _lines(out):
    return sorted(line for line in out.splitlines() if line.strip())


def _required_strength(iso):
    require = (iso or {}).get("require", "host")
    if require in ("namespace", None):
        return "host"
    return require


def _do_clone(sub, config, app, base_over, timeout):
    """Clone the app onto the substrate the way the config says. Returns
    (workdir, err) where err is None or a (reason, detail) pair. The clone runs
    *in the substrate*: for the host that is the host filesystem; for a fresh
    container the source is staged in and cloned there, so nothing lands on the
    host."""
    workroot = sub.workroot()
    src = config.get("source") or {}
    if src.get("clone"):
        sub_dir = src.get("dir", app)
        dest = os.path.join(workroot, sub_dir)
        rc, _ = sub.exec(f"test -d {shlex.quote(dest)}", workroot, base_over, 30)
        if rc != 0:
            clone_from = sub.stage(src["clone"])
            rc, tail = sub.exec(
                f"git clone {shlex.quote(clone_from)} {shlex.quote(dest)}",
                workroot, base_over, timeout)
            if rc != 0:
                return None, ("clone failed", tail)
        return dest, None
    if src.get("dir"):
        return os.path.join(workroot, src["dir"]), None
    return workroot, None


def run_envelope(config, target_dir, profile_name=None, timeout=DEFAULT_TIMEOUT,
                 until="full", operate=False):
    """Hoist and grade one config. Returns a report dict; never raises on a
    failed check (a failed check is data, not an exception).

    until="preflight" runs only the know-early pass (binds, isolation feasibility,
    and for the host floor the cheap probes + collision check) and stops before
    deploying anything: this is what the preflight operator runs to give a
    feasibility verdict without touching the target. until="full" (default)
    resolves (and provisions) the substrate, deploys, and grades.

    operate=True is the sysop path, distinct from grading: deploy and grade, but
    do NOT tear the substrate down. The live substrate is left running and stashed
    on the report under "_substrate_obj" so the caller can exec into it (petard
    harvests from a deploy that stays up, contract C) and tear it down explicitly
    when done. Prefer the operate() wrapper, which returns (report, substrate)."""
    profiles = config.get("profiles", {})
    if profile_name is None:
        profile_name = config.get("default_profile") or next(iter(profiles), None)
    if profile_name not in profiles:
        return {
            "app": config.get("app", "?"),
            "profile": profile_name,
            "outcome": "cannot-build",
            "reason": f"no such profile: {profile_name!r} (have {list(profiles)})",
        }
    profile = profiles[profile_name]
    app = config.get("app", "?")

    # The env the config/profile contribute. The substrate decides how to combine
    # it with its own base environment (the host merges os.environ; a fresh
    # container uses a clean env), so host state never leaks into a sandboxed run.
    base_over = {}
    for src in (config.get("env", {}), profile.get("env", {})):
        base_over.update({k: str(v) for k, v in src.items()})

    report = {
        "app": app, "profile": profile_name,
        "binds": [], "preflight": [], "bringup": [], "health": [],
        "acceptance": [], "did_not_transfer": [], "substrate": None,
    }

    # --- binds: host-side capability gate ----------------------------------
    # Binds answer "can this host even do the hoist": is docker here to run a
    # substrate, is git here to clone. They probe the host, before any substrate.
    host_env = {**os.environ, **base_over}
    for b in config.get("binds", []):
        rc, tail = _run(b["probe"], cwd=target_dir, timeout=timeout, env=host_env)
        ok = rc == 0
        report["binds"].append({"name": b["name"], "ok": ok})
        if not ok and b.get("required", True):
            report["outcome"] = "cannot-build"
            report["reason"] = f"missing required bind: {b['name']}"
            report["detail"] = tail
            return report

    # --- the non-destructive onboarding invariant --------------------------
    # A profile that deploys MUST declare isolation: either a same-host namespace
    # mapping, an isolation.require strength that resolves to an environmental
    # substrate, or isolation.none for a genuinely hermetic profile. A deploying
    # profile that declares nothing is REJECTED, never run.
    iso = profile.get("isolation")
    has_bringup = bool(_step_list(profile, "bringup"))
    if has_bringup and iso is None:
        report["outcome"] = "cannot-build"
        report["reason"] = (
            "refusing to deploy: profile has bringup but declares no isolation. "
            "Declare a namespace mapping, an isolation.require strength, or "
            "isolation:{\"none\":true,\"why\":...} if it starts no daemons, binds "
            "no host ports, and writes no shared state."
        )
        return report
    iso = iso or {}
    isolate = bool(profile.get("isolation")) and not iso.get("none")
    if iso.get("none"):
        report["isolation"] = {"none": True, "why": iso.get("why", "")}

    # --- preflight (know-early) path: report feasibility, deploy nothing ----
    if until == "preflight":
        feasible, sinfo = substrate.probe_substrate(config, profile, timeout)
        report["substrate"] = sinfo if feasible else {"resolved": False}
        if not feasible:
            report["outcome"] = "cannot-build"
            report["reason"] = sinfo
            return report
        # The host floor can be probed cheaply without provisioning anything. An
        # environmental rung cannot be probed inside without standing it up, and
        # preflight must touch nothing, so its feasibility is that the rung's
        # prerequisite resolved; the full checks run at deploy.
        if sinfo.get("strength") == "host":
            hostsub = substrate.HostSubstrate(target_dir)
            workdir, err = _do_clone(hostsub, config, app, base_over, timeout)
            if err:
                report["outcome"] = "cannot-build"
                report["reason"], report["detail"] = err
                return report
            for p in _step_list(profile, "preflight"):
                rc, tail = hostsub.exec(p["probe"], workdir, base_over, timeout)
                ok = rc == 0
                report["preflight"].append({"name": p["name"], "ok": ok})
                if not ok and p.get("required", True):
                    report["outcome"] = "cannot-build"
                    report["reason"] = f"preflight blocker: {p['name']}"
                    report["detail"] = tail
                    return report
            if isolate:
                namespace = f"hoist-{app}-{uuid.uuid4().hex[:8]}"
                report["isolation"] = {"namespace": namespace, "ports": {}}
                over = dict(base_over)
                if iso.get("namespace_env"):
                    over[iso["namespace_env"]] = namespace
                for pe in iso.get("port_envs", []):
                    port = _free_port()
                    over[pe] = str(port)
                    report["isolation"]["ports"][pe] = port
                cprobe = iso.get("collision_probe")
                if cprobe:
                    rc, tail = hostsub.exec(cprobe, workdir, over, timeout)
                    if rc != 0:
                        report["outcome"] = "cannot-build"
                        report["reason"] = (f"isolation collision: namespace "
                                            f"{namespace} is not clean")
                        report["detail"] = tail
                        return report
        report["outcome"] = "feasible"
        report["reason"] = ("binds, isolation, and cheap checks pass; deploy would "
                            "proceed")
        return report

    # --- full path: resolve (and provision) the substrate, deploy, grade ----
    # The environmental blast radius is verified after teardown by the substrate's
    # own residue (substrate.residue): our footprint is exactly its named
    # container, created after resolution and reclaimed by teardown, so a clean
    # hoist leaves no residue. This is checked one level up from a config's own
    # declared isolation -- it holds even for a config that ignores that block --
    # and is scoped to our own resources, so unrelated containers churning on a
    # shared host never register as a false violation.
    sub, sinfo = substrate.resolve_substrate(config, profile, target_dir, timeout)
    if sub is None:
        report["substrate"] = {"resolved": False}
        report["outcome"] = "cannot-build"
        report["reason"] = sinfo
        return report
    report["substrate"] = sinfo

    try:
        # --- source: clone the app onto the substrate ----------------------
        workdir, err = _do_clone(sub, config, app, base_over, timeout)
        if err:
            report["outcome"] = "cannot-build"
            report["reason"], report["detail"] = err
            return report
        report["workdir"] = workdir

        # --- preflight probes, in the substrate ----------------------------
        for p in _step_list(profile, "preflight"):
            rc, tail = sub.exec(p["probe"], workdir, base_over, timeout)
            ok = rc == 0
            report["preflight"].append({"name": p["name"], "ok": ok})
            if not ok and p.get("required", True):
                report["outcome"] = "cannot-build"
                report["reason"] = f"preflight blocker: {p['name']}"
                report["detail"] = tail
                return report

        # --- isolation: host floor uses the config's namespace; an
        #     environmental rung IS the isolation boundary --------------------
        deploy_over = dict(base_over)
        blast_probe = None
        if sub.strength == "host" and isolate:
            namespace = f"hoist-{app}-{uuid.uuid4().hex[:8]}"
            report["isolation"] = {"namespace": namespace, "ports": {}}
            if iso.get("namespace_env"):
                deploy_over[iso["namespace_env"]] = namespace
            for pe in iso.get("port_envs", []):
                port = _free_port()
                deploy_over[pe] = str(port)
                report["isolation"]["ports"][pe] = port
            cprobe = iso.get("collision_probe")
            if cprobe:
                rc, tail = sub.exec(cprobe, workdir, deploy_over, timeout)
                if rc != 0:
                    report["outcome"] = "cannot-build"
                    report["reason"] = (f"isolation collision: namespace "
                                        f"{namespace} is not clean")
                    report["detail"] = tail
                    return report
            blast_probe = iso.get("blast_radius_probe")
        elif sub.strength != "host":
            report["isolation"] = {"substrate": sinfo.get("name"),
                                  "strength": sinfo.get("strength"),
                                  "why": "the substrate is the isolation boundary"}

        # --- blast radius before (host floor: the config's per-namespace
        #     probe; environmental: the host-daemon snapshot taken above) -----
        blast_before = None
        if blast_probe:
            _, out = sub.exec(blast_probe, workdir, deploy_over, timeout)
            blast_before = _lines(out)

        # --- bringup: the install gate -------------------------------------
        bringup_ok = True
        for s in _step_list(profile, "bringup"):
            rc, tail = sub.exec(s["run"], workdir, deploy_over, timeout)
            ok = rc == 0
            report["bringup"].append(
                {"name": s["name"], "ok": ok, **({} if ok else {"detail": tail})})
            if not ok:
                bringup_ok = False
                report["did_not_transfer"].append(f"bringup:{s['name']}")

        # --- health: is it actually up -------------------------------------
        health_up = health_total = 0
        if bringup_ok:
            for h in _step_list(profile, "health"):
                health_total += 1
                rc, tail = sub.exec(h["check"], workdir, deploy_over, timeout)
                ok = rc == 0
                report["health"].append(
                    {"name": h["name"], "ok": ok, **({} if ok else {"detail": tail})})
                if ok:
                    health_up += 1
                else:
                    report["did_not_transfer"].append(f"health:{h['name']}")
        report["health_score"] = [health_up, health_total]

        # --- acceptance: the held-back honest transfer score ---------------
        acc_pass = acc_total = 0
        install_up = bringup_ok and health_up == health_total
        if install_up:
            for c in _step_list(profile, "acceptance"):
                acc_total += 1
                rc, tail = sub.exec(c["check"], workdir, deploy_over, timeout)
                ok = rc == 0
                report["acceptance"].append(
                    {"name": c["name"], "ok": ok, **({} if ok else {"detail": tail})})
                if ok:
                    acc_pass += 1
                else:
                    report["did_not_transfer"].append(f"acceptance:{c['name']}")
        report["transfer_score"] = round(acc_pass / acc_total, 4) if acc_total else 0.0
        report["transfer"] = [acc_pass, acc_total]

        # --- outcome -------------------------------------------------------
        if not install_up:
            report["outcome"] = "honest-failure"
            report["reason"] = "did not come up cleanly on this target"
        elif acc_total and acc_pass == acc_total:
            report["outcome"] = "built"
            report["reason"] = "install gate up, all acceptance checks passed"
        else:
            report["outcome"] = "honest-failure"
            report["reason"] = "came up, but not everything transferred"

        # --- teardown (host floor: the config's namespace teardown) --------
        if sub.strength == "host" and isolate and iso.get("teardown") and has_bringup:
            rc, tail = sub.exec(iso["teardown"], workdir, deploy_over, timeout)
            report["teardown"] = {"ran": True, "ok": rc == 0,
                                 **({} if rc == 0 else {"detail": tail})}

        # --- blast radius after (host floor per-namespace probe) -----------
        if blast_before is not None:
            _, out = sub.exec(blast_probe, workdir, deploy_over, timeout)
            blast_after = _lines(out)
            clean = blast_after == blast_before
            report["blast_radius"] = {"clean": clean,
                                     "protected_before": len(blast_before),
                                     "protected_after": len(blast_after)}
            if not clean:
                report["did_not_transfer"].append(
                    "blast_radius:touched-pre-existing-state")

        return report
    finally:
        # operate mode (sysop): leave the substrate running and hand it back, so
        # the deploy stays up for petard to harvest from and for the caller to tear
        # down explicitly. The environmental blast-radius check moves to that
        # explicit teardown (the caller owns it), since the substrate is up on
        # purpose here.
        if operate and sub is not None and sub.name != "host":
            report["_substrate_obj"] = sub
            if isinstance(report.get("substrate"), dict):
                report["substrate"]["operating"] = True
        # Grade mode: an environmental substrate is always torn down, whatever the
        # outcome, so onboarding adds nothing lasting. Run the config's own teardown
        # inside it first (best-effort), then destroy the substrate, then verify the
        # environmental guarantee by our own residue: no host resource of ours
        # remains. Scoped to our footprint, so it holds even for a config that
        # ignored its own isolation, and is not fooled by unrelated host churn.
        elif sub is not None and sub.name != "host":
            if isolate and iso.get("teardown") and has_bringup and "workdir" in report:
                sub.exec(iso["teardown"], report["workdir"], base_over, timeout)
            ok, _ = sub.teardown()
            if isinstance(report.get("substrate"), dict):
                report["substrate"]["torn_down"] = ok
            residue = sub.residue()
            report["blast_radius"] = {"clean": not residue, "residue": residue}
            if residue:
                report["did_not_transfer"].append(
                    "blast_radius:substrate-residue-remains")


def operate(config, target_dir=None, profile_name=None, timeout=DEFAULT_TIMEOUT):
    """The sysop path: deploy and grade one config, then KEEP IT RUNNING. Returns
    (report, substrate). The substrate is live; exec into it with substrate.exec
    (petard harvests its command surface this way, contract C) and destroy it with
    substrate.teardown() when done. For a host-floor deploy there is no separate
    substrate to keep, so the returned substrate is the HostSubstrate and teardown
    is a no-op. Never auto-tears-down: that is the caller's explicit call."""
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="hoist-operate-")
    os.makedirs(target_dir, exist_ok=True)
    report = run_envelope(config, target_dir, profile_name, timeout,
                          until="full", operate=True)
    sub = report.pop("_substrate_obj", None)
    if sub is None:
        # cannot-build / honest-failure before an environmental substrate stood up,
        # or a host-floor deploy: hand back a resolved handle so the caller has a
        # uniform (report, substrate) contract and a teardown to call.
        sub = substrate.HostSubstrate(target_dir)
    return report, sub


def format_report(r):
    lines = []
    o = r["outcome"]
    banner = {"built": "BUILT", "honest-failure": "HONEST-FAILURE",
              "cannot-build": "CANNOT-BUILD", "feasible": "FEASIBLE"}.get(o, o.upper())
    lines.append(f"{banner}  [{r['app']} / {r.get('profile','?')}]  {r.get('reason','')}")
    sub = r.get("substrate")
    if isinstance(sub, dict) and sub.get("name"):
        strength = sub.get("strength", "?")
        note = "" if strength != "host" else " (same-host namespace: a deploy can still reach host state)"
        lines.append(f"  substrate: {sub['name']} / {strength}{note}")
    if o == "cannot-build":
        if r.get("detail"):
            lines.append(f"  detail: {r['detail'].splitlines()[-1] if r['detail'] else ''}")
        return "\n".join(lines)
    if o == "feasible":
        ns = r.get("isolation", {}).get("namespace")
        if ns:
            lines.append(f"  would deploy into isolated namespace {ns}; nothing deployed")
        return "\n".join(lines)
    hs = r.get("health_score", [0, 0])
    lines.append(f"  install gate: {hs[0]}/{hs[1]} healthy")
    tr = r.get("transfer", [0, 0])
    lines.append(f"  transfer score: {tr[0]}/{tr[1]}  ({r.get('transfer_score', 0.0)})")
    for c in r.get("acceptance", []):
        mark = "ok  " if c["ok"] else "FAIL"
        lines.append(f"    [{mark}] {c['name']}")
    br = r.get("blast_radius")
    if br and not br.get("clean"):
        lines.append("  ** BLAST RADIUS VIOLATED: the hoist changed state outside its "
                     "namespace despite declaring isolation **")
    elif br and r.get("substrate", {}).get("strength") not in (None, "host"):
        lines.append("  blast radius clean: the substrate left no residue on the host")
    if r.get("did_not_transfer"):
        lines.append("  did not transfer: " + ", ".join(r["did_not_transfer"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hoistable honest-grade envelope runner")
    ap.add_argument("config", help="path to a Layer 2 config JSON")
    ap.add_argument("--profile", default=None, help="deployment profile to hoist")
    ap.add_argument("--target-dir", default=None,
                    help="clean target to hoist onto (default: a temp dir)")
    ap.add_argument("--json-out", default=None, help="write the JSON report here")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--until", choices=["full", "preflight"], default="full",
                    help="preflight = know-early pass only, deploys nothing")
    args = ap.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    tmp = None
    target = args.target_dir
    if not target:
        tmp = tempfile.mkdtemp(prefix="hoist-target-")
        target = tmp
    os.makedirs(target, exist_ok=True)

    report = run_envelope(config, target, args.profile, args.timeout, until=args.until)
    print(format_report(report))
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)

    # Exit code: 0 built/feasible, 1 honest-failure, 2 cannot-build. A grader can branch.
    return {"built": 0, "feasible": 0, "honest-failure": 1,
            "cannot-build": 2}.get(report["outcome"], 3)


if __name__ == "__main__":
    sys.exit(main())
