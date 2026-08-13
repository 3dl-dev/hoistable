#!/usr/bin/env python3
"""Hoistable's honest-grade envelope runner.

The neutral core of build-rule 7 ("no silent success"). It takes a Layer 2
config, hoists the app onto a target the way the config says to, and grades the
result honestly. It never claims a success it did not earn.

The shape is skillc's envelope applied to a deployable system instead of a voice:

  - binds        the local capabilities the config requires (docker, a secret).
                 A missing required bind is a CANNOT-BUILD: named, and we stop.
  - preflight    cheap probes run before deploy, so the user learns at the door.
                 A required preflight blocker is also a CANNOT-BUILD.
  - bringup      clone + configure + deploy the chosen profile. The install gate.
  - health       is the system actually up. Counted N of M.
  - acceptance   the held-back checks. Their pass fraction is the honest transfer
                 score: whether the app really works here, not just came up.

Three plain outcomes, exactly as skillc reports:
  - built           install gate up and every acceptance check passed.
  - honest-failure  it came up but something did not transfer; we say what.
  - cannot-build    a required bind or a preflight blocker is missing, named.

Standard library only (build-rule 3). The config is data; this runner is generic.
App specifics live in the config, never here (build-rule 6, point don't embed).
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


DEFAULT_TIMEOUT = 600


def _run(cmd, cwd, timeout=DEFAULT_TIMEOUT, env=None):
    """Run a shell command, return (rc, tail-of-output)."""
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


def run_envelope(config, target_dir, profile_name=None, timeout=DEFAULT_TIMEOUT,
                 until="full"):
    """Hoist and grade one config. Returns a report dict; never raises on a
    failed check (a failed check is data, not an exception).

    until="preflight" runs only the know-early pass (binds, preflight probes,
    isolation checks) and stops before deploying anything: this is what the
    preflight operator runs to give a feasibility verdict without touching the
    target. until="full" (default) deploys and grades."""
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
    # Env overrides let a config isolate its deployment namespace (a unique
    # COMPOSE_PROJECT_NAME, remapped host ports) so a same-host hoist cannot
    # collide with an already-running instance. Applied to every step.
    run_env = dict(os.environ)
    for src in (config.get("env", {}), profile.get("env", {})):
        run_env.update({k: str(v) for k, v in src.items()})
    report = {
        "app": app,
        "profile": profile_name,
        "binds": [],
        "preflight": [],
        "bringup": [],
        "health": [],
        "acceptance": [],
        "did_not_transfer": [],
    }

    # --- binds: missing required capability -> cannot-build, named, stop -----
    for b in config.get("binds", []):
        rc, tail = _run(b["probe"], cwd=target_dir, timeout=timeout, env=run_env)
        ok = rc == 0
        report["binds"].append({"name": b["name"], "ok": ok})
        if not ok and b.get("required", True):
            report["outcome"] = "cannot-build"
            report["reason"] = f"missing required bind: {b['name']}"
            report["detail"] = tail
            return report

    # --- source: clone the app onto the target ------------------------------
    src = config.get("source") or {}
    workdir = target_dir
    if src.get("clone"):
        sub = src.get("dir", app)
        dest = os.path.join(target_dir, sub)
        if not os.path.isdir(dest):
            rc, tail = _run(f"git clone {shlex.quote(src['clone'])} {shlex.quote(dest)}",
                            cwd=target_dir, timeout=timeout, env=run_env)
            if rc != 0:
                report["outcome"] = "cannot-build"
                report["reason"] = "clone failed"
                report["detail"] = tail
                return report
        workdir = dest
    elif src.get("dir"):
        workdir = os.path.join(target_dir, src["dir"])
    report["workdir"] = workdir

    # --- preflight: cheap probes before deploy, know early ------------------
    for p in _step_list(profile, "preflight"):
        rc, tail = _run(p["probe"], cwd=workdir, timeout=timeout, env=run_env)
        ok = rc == 0
        report["preflight"].append({"name": p["name"], "ok": ok})
        if not ok and p.get("required", True):
            report["outcome"] = "cannot-build"
            report["reason"] = f"preflight blocker: {p['name']}"
            report["detail"] = tail
            return report

    # --- isolation: onboarding must never touch pre-existing target state ---
    # The non-destructive onboarding invariant, enforced structurally. A profile
    # that deploys MUST declare isolation. The runner then owns a fresh namespace
    # (a unique name, its own host ports) and refuses to proceed unless that
    # namespace is verified empty. A deploying profile that declares no isolation
    # is REJECTED, never run: this is the guard that stops a hoist from
    # re-asserting an app's own singular deployment on a host that already runs
    # it. A genuinely hermetic profile must say so on purpose, with a reason.
    iso = profile.get("isolation")
    has_bringup = bool(_step_list(profile, "bringup"))
    if has_bringup and iso is None:
        report["outcome"] = "cannot-build"
        report["reason"] = (
            "refusing to deploy: profile has bringup but declares no isolation. "
            "Declare a namespace mapping, or isolation:{\"none\":true,\"why\":...} "
            "if it starts no daemons, binds no host ports, and writes no shared state."
        )
        return report
    isolate = bool(iso) and not iso.get("none")
    if iso and iso.get("none"):
        report["isolation"] = {"none": True, "why": iso.get("why", "")}
    if isolate:
        namespace = f"hoist-{app}-{uuid.uuid4().hex[:8]}"
        report["isolation"] = {"namespace": namespace, "ports": {}}
        if iso.get("namespace_env"):
            run_env[iso["namespace_env"]] = namespace
        for pe in iso.get("port_envs", []):
            port = _free_port()
            run_env[pe] = str(port)
            report["isolation"]["ports"][pe] = port
        probe = iso.get("collision_probe")
        if probe:
            rc, tail = _run(probe, cwd=workdir, timeout=timeout, env=run_env)
            if rc != 0:
                report["outcome"] = "cannot-build"
                report["reason"] = f"isolation collision: namespace {namespace} is not clean"
                report["detail"] = tail
                return report

    # If we are only running preflight (the operator's know-early pass), stop
    # here: everything up to deploy has passed, and we have touched nothing.
    if until == "preflight":
        report["outcome"] = "feasible"
        report["reason"] = "binds, preflight, and isolation checks pass; deploy would proceed"
        return report

    # --- bringup: the install gate -----------------------------------------
    bringup_ok = True
    for s in _step_list(profile, "bringup"):
        rc, tail = _run(s["run"], cwd=workdir, timeout=timeout, env=run_env)
        ok = rc == 0
        report["bringup"].append(
            {"name": s["name"], "ok": ok, **({} if ok else {"detail": tail})}
        )
        if not ok:
            bringup_ok = False
            report["did_not_transfer"].append(f"bringup:{s['name']}")

    # --- health: is it actually up -----------------------------------------
    health_up = 0
    health_total = 0
    if bringup_ok:
        for h in _step_list(profile, "health"):
            health_total += 1
            rc, tail = _run(h["check"], cwd=workdir, timeout=timeout, env=run_env)
            ok = rc == 0
            report["health"].append(
                {"name": h["name"], "ok": ok, **({} if ok else {"detail": tail})}
            )
            if ok:
                health_up += 1
            else:
                report["did_not_transfer"].append(f"health:{h['name']}")
    report["health_score"] = [health_up, health_total]

    # --- acceptance: the held-back honest transfer score -------------------
    acc_pass = 0
    acc_total = 0
    install_up = bringup_ok and health_up == health_total
    if install_up:
        for c in _step_list(profile, "acceptance"):
            acc_total += 1
            rc, tail = _run(c["check"], cwd=workdir, timeout=timeout, env=run_env)
            ok = rc == 0
            report["acceptance"].append(
                {"name": c["name"], "ok": ok, **({} if ok else {"detail": tail})}
            )
            if ok:
                acc_pass += 1
            else:
                report["did_not_transfer"].append(f"acceptance:{c['name']}")
    report["transfer_score"] = round(acc_pass / acc_total, 4) if acc_total else 0.0
    report["transfer"] = [acc_pass, acc_total]

    # --- outcome -----------------------------------------------------------
    if not install_up:
        report["outcome"] = "honest-failure"
        report["reason"] = "did not come up cleanly on this target"
    elif acc_total and acc_pass == acc_total:
        report["outcome"] = "built"
        report["reason"] = "install gate up, all acceptance checks passed"
    else:
        report["outcome"] = "honest-failure"
        report["reason"] = "came up, but not everything transferred"

    # --- teardown: a hoist leaves the target as it found it -----------------
    # Always tear down the isolated namespace once graded, whatever the outcome,
    # so onboarding adds nothing lasting and removes nothing it did not create.
    if isolate and iso.get("teardown") and has_bringup:
        rc, tail = _run(iso["teardown"], cwd=workdir, timeout=timeout, env=run_env)
        report["teardown"] = {"ran": True, "ok": rc == 0,
                              **({} if rc == 0 else {"detail": tail})}
    return report


def format_report(r):
    lines = []
    o = r["outcome"]
    banner = {"built": "BUILT", "honest-failure": "HONEST-FAILURE",
              "cannot-build": "CANNOT-BUILD", "feasible": "FEASIBLE"}.get(o, o.upper())
    lines.append(f"{banner}  [{r['app']} / {r.get('profile','?')}]  {r.get('reason','')}")
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
