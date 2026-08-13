#!/usr/bin/env python3
"""hoist: the Layer 1 entry point (the "brew"), driver side.

Given an app's Layer 2 config, hoist drives the whole onboarding. It runs the
preflight know-early pass first, deploying nothing, and only if that is feasible
does it deploy and grade. It never drops the user at a blank prompt: each step
announces what it is doing and ends in a plain outcome.

This is the mechanical driver. The two things that make hoist Homebrew-shaped
live in the hoist skill (SKILL.md), which calls this:
  - discovery: finding an app's config like brew finds a formula (an index, a
    GitHub URL, a web search). resolve_config here implements the local-path
    case and marks the rest as extension points.
  - authoring: building a config for an app that has none, making the user its
    author. That is a Claude-run authoring pass, not this driver.

Standard library only. The grading and the non-destructive onboarding invariant
live in envelope.py; hoist just sequences the two passes over it.
"""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "envelope"))
import envelope  # noqa: E402


def resolve_config(ref):
    """Resolve a config reference to a loaded config dict. Local path is
    implemented; an index lookup and a GitHub/web URL are extension points the
    hoist skill fills in."""
    if os.path.isfile(ref):
        with open(ref) as f:
            return json.load(f)
    raise SystemExit(
        f"could not resolve config: {ref!r} "
        "(only local paths are implemented; index/URL discovery is a skill extension point)"
    )


def _indent(text):
    return "  " + text.replace("\n", "\n  ")


def hoist(ref, profile=None, target_dir=None, timeout=envelope.DEFAULT_TIMEOUT, emit=print):
    """Drive an onboarding: preflight (deploy nothing) then, if feasible,
    deploy and grade. Returns the final report."""
    config = resolve_config(ref)
    app = config.get("app", "?")
    prof = profile or config.get("default_profile") or "default"
    if not target_dir:
        target_dir = tempfile.mkdtemp(prefix="hoist-target-")
    os.makedirs(target_dir, exist_ok=True)

    emit(f"hoist: onboarding {app} (profile {prof})")
    emit("  [1/2] preflight: checking the target, deploying nothing ...")
    pf = envelope.run_envelope(config, target_dir, profile, timeout, until="preflight")
    emit(_indent(envelope.format_report(pf)))
    if pf["outcome"] != "feasible":
        emit(f"hoist: stopped at the door ({pf['outcome']}). Nothing was deployed.")
        return pf

    emit("  [2/2] deploy and grade ...")
    full = envelope.run_envelope(config, target_dir, profile, timeout, until="full")
    emit(_indent(envelope.format_report(full)))
    emit(f"hoist: {full['outcome']} for {app}.")
    return full


def main(argv=None):
    ap = argparse.ArgumentParser(description="hoist an app from its Layer 2 config")
    ap.add_argument("config", help="config path (index/URL discovery is a skill extension point)")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--target-dir", default=None)
    ap.add_argument("--timeout", type=int, default=envelope.DEFAULT_TIMEOUT)
    args = ap.parse_args(argv)
    r = hoist(args.config, args.profile, args.target_dir, args.timeout)
    return {"built": 0, "feasible": 0, "honest-failure": 1,
            "cannot-build": 2}.get(r["outcome"], 3)


if __name__ == "__main__":
    sys.exit(main())
