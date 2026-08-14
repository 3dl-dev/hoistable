#!/usr/bin/env python3
"""develop: understand how to iterate on a hoisted app, from its ground truth.

Before a self-hoster can develop an app, they need to know how it is built,
tested, and contributed to. This harvests that from the project's own ground
truth (the same discipline as petard: generated, never authored): Makefile
targets, a CONTRIBUTING file, CI workflows, package scripts, and the test files
themselves. The result is a dev guide the user can act on: how to test, how to
build, where the contribution path is.

Standard library only.
"""

import argparse
import glob
import json
import os
import sys


def _makefile_targets(path):
    targets, doc = {}, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f.read().splitlines():
            if line.startswith("##"):
                doc.append(line.lstrip("#").strip())
            elif line and line[0].isalnum() and ":" in line.split()[0]:
                t = line.split(":", 1)[0].strip()
                if t and t != ".PHONY":
                    targets[t] = " ".join(d for d in doc if d).strip()
                doc = []
            elif line.strip():
                doc = []
    return targets


def dev_guide(repo):
    g = {"test": [], "build_or_run": [], "make_targets": {}, "contributing": None,
         "ci": [], "npm_scripts": {}}

    mk = os.path.join(repo, "Makefile")
    if os.path.isfile(mk):
        g["make_targets"] = _makefile_targets(mk)
        for t in g["make_targets"]:
            if "test" in t:
                g["test"].append(f"make {t}")
            if t in ("build", "dev", "up", "install", "run"):
                g["build_or_run"].append(f"make {t}")

    for name in ("CONTRIBUTING.md", "CONTRIBUTING", "docs/CONTRIBUTING.md", ".github/CONTRIBUTING.md"):
        if os.path.isfile(os.path.join(repo, name)):
            g["contributing"] = name
            break

    wf = os.path.join(repo, ".github", "workflows")
    if os.path.isdir(wf):
        g["ci"] = sorted(n for n in os.listdir(wf) if n.endswith((".yml", ".yaml")))

    pj = os.path.join(repo, "package.json")
    if os.path.isfile(pj):
        try:
            with open(pj) as f:
                g["npm_scripts"] = json.load(f).get("scripts", {})
        except (OSError, ValueError):
            pass
        for k in g["npm_scripts"]:
            g["test"].append("npm test" if k == "test" else f"npm run {k}") if "test" in k else None

    _noise = ("__pycache__", ".git", "node_modules", ".venv", "/dist/", "/build/")
    for t in sorted(glob.glob(os.path.join(repo, "**", "test_*.py"), recursive=True)):
        rel = os.path.relpath(t, repo)
        if any(n.strip("/") in rel.split(os.sep) or n in "/" + rel + "/" for n in _noise):
            continue
        cmd = f"python3 {rel}"
        if cmd not in g["test"]:
            g["test"].append(cmd)

    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description="harvest a dev guide from a repo's ground truth")
    ap.add_argument("repo")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    g = dev_guide(args.repo)
    text = json.dumps(g, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text + "\n")
        print(f"dev guide -> {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
