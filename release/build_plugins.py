#!/usr/bin/env python3
"""Regenerate the committed plugin skills from their single source.

The `plugins/` SKILL.md files are BUILD ARTIFACTS, generated from the canonical sources
(`builder/SKILL.md`, `hoist/SKILL.md`) plus the toolchain bootstrap and a harness pin.
Committing the generated copy is required for the marketplace to serve it, but it must
never be hand-edited: edit the source and re-run this. Cutting a release is
`build_release.py` (the kit) then this (pin the release into the plugins). This kills the
drift hazard of two copies maintained by hand.

Standard library only.
"""

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_HERE, "..")


def _bootstrap(pin):
    seed = open(os.path.join(ROOT, "builder", "seed", "toolchain-bootstrap.md")).read()
    return seed.replace("<pin>", json.dumps(pin, indent=2))


def _assemble(src_rel, skill_name, pin):
    parts = open(os.path.join(ROOT, src_rel)).read().split("---", 2)
    fm = re.sub(r"name: .*", f"name: {skill_name}", parts[1], count=1)
    return "---" + fm + "---\n\n" + _bootstrap(pin) + "\n" + parts[2].lstrip("\n")


# The single source of each committed plugin skill: (source file, skill name, output path).
PLUGIN_SKILLS = [
    ("builder/SKILL.md", "build", "plugins/hoistable/skills/build/SKILL.md"),
    ("hoist/SKILL.md", "run", "plugins/hoistable/skills/run/SKILL.md"),
]


def build_plugins(pin):
    written = []
    for src, name, out in PLUGIN_SKILLS:
        p = os.path.join(ROOT, out)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(_assemble(src, name, pin))
        written.append(out)
    return written


def current_pin():
    """The pin already stamped in the committed build skill (for a no-op regen)."""
    t = open(os.path.join(ROOT, "plugins/hoistable/skills/build/SKILL.md")).read()
    return json.loads(re.search(r"```json\n(\{.*?\})\n```", t, re.S).group(1))


def main(argv=None):
    ap = argparse.ArgumentParser(description="regenerate committed plugin skills from source")
    ap.add_argument("--pin", help="JSON file with {version, url, sha256}; default: keep current pin")
    args = ap.parse_args(argv)
    pin = json.load(open(args.pin)) if args.pin else current_pin()
    pin = pin.get("operators", pin)
    for f in build_plugins(pin):
        print("regenerated", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
