#!/usr/bin/env python3
"""Regenerate the committed plugin skills from their single source.

The `plugins/` SKILL.md files are BUILD ARTIFACTS, copied from the canonical sources
(`builder/SKILL.md`, `hoist/SKILL.md`) with only the plugin skill name set in the
frontmatter. Committing the generated copy is required for the marketplace to serve it,
but it must never be hand-edited: edit the source and re-run this. This kills the drift
hazard of two copies maintained by hand.

There is no toolchain and no pin to inject: the skills carry nothing to fetch or run. A
receiver's agent follows the skill in its own session. Standard library only.
"""

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_HERE, "..")          # core/ : the skill sources (builder, hoist)
REPO = os.path.join(ROOT, "..")           # repo root : the committed plugins/ artifact


def _assemble(src_rel, skill_name):
    """The plugin skill is the source skill verbatim, with its frontmatter `name:` set to
    the plugin's skill name. Nothing is prepended; the skill is self-contained."""
    head, fm, body = open(os.path.join(ROOT, src_rel)).read().split("---", 2)
    fm = re.sub(r"name: .*", f"name: {skill_name}", fm, count=1)
    return "---" + fm + "---" + body


# The single source of each committed plugin skill: (source file, skill name, output path).
PLUGIN_SKILLS = [
    ("builder/SKILL.md", "build", "plugins/hoistable/skills/build/SKILL.md"),
    ("hoist/SKILL.md", "run", "plugins/hoistable/skills/run/SKILL.md"),
]


def build_plugins():
    written = []
    for src, name, out in PLUGIN_SKILLS:
        p = os.path.join(REPO, out)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(_assemble(src, name))
        written.append(out)
    return written


def main(argv=None):
    argparse.ArgumentParser(
        description="regenerate committed plugin skills from source").parse_args(argv)
    for f in build_plugins():
        print("regenerated", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
