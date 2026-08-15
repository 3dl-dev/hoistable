#!/usr/bin/env python3
"""Self-test for the plugin-skill copier (core/release/build_plugins.py). Stdlib only.

The committed plugins/ SKILL.md files are BUILD ARTIFACTS: each is its canonical source
verbatim, with only the frontmatter `name:` set to the plugin skill name. This suite guards
the drift hazard the copier exists to kill: it regenerates every declared plugin skill and
asserts the committed file already matches (name set, body byte-for-byte the source body),
so a hand-edit of an artifact or a stale checkout fails here. It also re-checks that each
plugin skill carries nothing of ours to fetch or run.

Run: python3 tests/test_plugins.py
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "release"))
import build_plugins as bp  # noqa: E402

REPO = os.path.join(HERE, "..")

# Same confound strings as the builder suite: a plugin skill is a self-contained recipe an
# agent follows in-session, never an instruction to fetch and run a toolchain of ours.
CONFOUND = ["self-extract the runtime", "sha256", ".tgz", "toolchain pin",
            "operators pin", "hoist.py", "envelope.py", "fetch the tarball",
            "verify the pin"]


class TestPluginCopier(unittest.TestCase):
    def test_every_committed_artifact_matches_regeneration(self):
        """The committed artifact equals what the copier would write right now (no drift)."""
        for src, name, out in bp.PLUGIN_SKILLS:
            with self.subTest(out=out):
                regenerated = bp._assemble(src, name)
                committed = open(os.path.join(REPO, out)).read()
                self.assertEqual(committed, regenerated,
                                 f"{out} drifted from {src}; run build_plugins.py")

    def test_name_is_set_and_body_is_verbatim(self):
        """`name:` is the plugin skill name; everything after frontmatter is the source body."""
        for src, name, out in bp.PLUGIN_SKILLS:
            with self.subTest(out=out):
                gen = bp._assemble(src, name)
                _, fm, body = gen.split("---", 2)
                self.assertIn(f"name: {name}", fm)
                src_body = open(os.path.join(bp.ROOT, src)).read().split("---", 2)[2]
                self.assertEqual(body, src_body)

    def test_optimize_loop_is_wired_in(self):
        """The optimize-loop skill ships as the /hoistable:optimize plugin skill."""
        names = {name for _, name, _ in bp.PLUGIN_SKILLS}
        self.assertIn("optimize", names)
        srcs = {src for src, _, _ in bp.PLUGIN_SKILLS}
        self.assertIn("optimize-loop/SKILL.md", srcs)

    def test_no_toolchain_leaked_into_any_plugin_skill(self):
        for src, name, _ in bp.PLUGIN_SKILLS:
            with self.subTest(src=src):
                text = bp._assemble(src, name).lower()
                for c in CONFOUND:
                    self.assertNotIn(c.lower(), text,
                                     f"{src} leaks '{c}': a plugin skill fetches/runs nothing of ours")


if __name__ == "__main__":
    r = unittest.main(argv=[sys.argv[0], "-v"], exit=False, verbosity=1).result
    print(f"{'PASS' if r.wasSuccessful() else 'FAIL'} test_plugins "
          f"({r.testsRun} cases)")
    sys.exit(0 if r.wasSuccessful() else 1)
