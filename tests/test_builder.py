#!/usr/bin/env python3
"""Self-test for the hoist builder (use case 1): assemble an app as ONE self-contained
distributable hoist SKILL. Stdlib only, hermetic.

This grades the ASSEMBLY only: the emitted file is one self-contained skill, it stamps the
honest-grade discipline as prose, carries the app's recipe inlined, declares
binds/checks/acceptance, is deterministic, and is self-extracting (extract_config recovers
the carried recipe from the one file). It also proves what the reshape guarantees: the
emitted skill carries NO toolchain, no pin, nothing of ours to fetch or run. The receiver
agent does the hoist in its own session.

There is deliberately no "run the spine to grade" test here. Grading the product means an
agent following the emitted skill on a real target (the ouroboros), not this process
running our Python. That grade lives in grade/, not in this suite.

Run: python3 tests/test_builder.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "builder"))
import emit  # noqa: E402

# These confound strings must NEVER appear in an emitted skill: they would tell the
# receiver to fetch and run a toolchain of ours, which is the inversion this project exists
# to avoid. The product is a skill; the agent does the work in-context.
CONFOUND = ["self-extract the runtime", "sha256", ".tgz", "toolchain pin",
            "operators pin", "hoist.py", "envelope.py", "fetch the tarball",
            "verify the pin"]


def _toy_app_dir(test, name="toy"):
    """A hermetic toy app: isolation none, bringup writes a marker in its throwaway
    target, acceptance checks it. Used for shape assertions only. `test` is the
    TestCase, so the throwaway dir is torn down when the case finishes (hermetic:
    the suite leaves no shared state in /tmp)."""
    d = tempfile.mkdtemp(prefix=f"builder-{name}-")
    test.addCleanup(shutil.rmtree, d, ignore_errors=True)
    config = {
        "app": name,
        "binds": [{"name": "sh", "probe": "sh -c 'exit 0'", "required": True}],
        "default_profile": "default",
        "profiles": {"default": {
            "isolation": {"none": True,
                          "why": "hermetic toy: writes only a marker in its throwaway target"},
            "bringup": [{"name": "write-marker", "run": "echo up > marker"}],
            "health": [{"name": "marker", "check": "test -f marker"}],
            "acceptance": [
                {"name": "marker-present", "check": "test -f marker"},
                {"name": "marker-content", "check": "grep -q up marker"},
            ],
        }},
    }
    with open(os.path.join(d, "config.json"), "w") as f:
        json.dump(config, f)
    return d, config


class EmitShape(unittest.TestCase):

    def test_default_output_carries_no_hoistable_branding(self):
        # the emitted skill is the developer's product; by default it names nothing of
        # ours, so a developer who does nothing still ships something app-first.
        app_dir, _ = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir)
        header = "\n".join(text.splitlines()[:4])
        self.assertTrue(text.startswith("---\nname: deploy\n"))
        self.assertNotIn("hoist", header.lower())      # not in name or description

    def test_developer_can_brand_the_output(self):
        app_dir, _ = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir, skill_name="up",
                              description="Bring toy up on your box.")
        self.assertTrue(text.startswith("---\nname: up\n"))
        self.assertIn("Bring toy up on your box.", text)

    def test_description_with_a_colon_stays_valid_frontmatter(self):
        # a ': ' in a description must not break YAML; it is quoted, not left raw.
        app_dir, _ = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir, description="Deploy toy: fast and safe.")
        line = [l for l in text.splitlines() if l.startswith("description:")][0]
        self.assertEqual(line, 'description: "Deploy toy: fast and safe."')

    def test_scaffold_marketplace_is_self_host_ready_and_unbranded(self):
        app_dir, _ = _toy_app_dir(self, "toy")
        out = tempfile.mkdtemp(prefix="scaffold-")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        inv = emit.scaffold_marketplace(out, app_dir, marketplace_name="mytap",
                                       plugin_name="toy", skill_name="up",
                                       description="Bring toy up.")
        self.assertEqual(inv, "/toy:up")                 # what their users type
        mkt = json.load(open(os.path.join(out, ".claude-plugin", "marketplace.json")))
        self.assertEqual(mkt["name"], "mytap")
        self.assertEqual(mkt["plugins"][0]["name"], "toy")
        skill = open(os.path.join(out, "plugins", "toy", "skills", "up", "SKILL.md")).read()
        self.assertTrue(skill.startswith("---\nname: up\n"))
        self.assertNotIn("hoist", "\n".join(skill.splitlines()[:4]).lower())

    def test_stamps_the_hoist_discipline_as_prose(self):
        app_dir, _ = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir)
        # the discipline is stamped verbatim, with <app> and <verb> resolved
        self.assertIn("This skill sets toy up before it reports toy is up", text)
        self.assertIn("## The hoist discipline", text)
        self.assertIn("deploy it against", text)      # the neutral verb, not "hoist it"
        for step in ("Binds gate", "Resolve the isolation", "Preflight",
                     "held-back", "Land it", "cannot-build"):
            self.assertIn(step, text)
        # the OBJECTIVE is a running app, not a teardown of what the user asked for
        self.assertIn("leave toy running", text)
        self.assertIn("to sysop to keep it up", text)
        self.assertNotIn("teardown always runs", text)   # teardown is not the success path
        # binds, checks, acceptance all present
        self.assertIn("## Binds", text)
        self.assertIn("## Checks", text)
        self.assertIn("## Acceptance", text)
        self.assertIn("`marker-present`", text)

    def test_the_emitted_skill_ships_nothing_to_fetch_or_run(self):
        # the core guarantee of the reshape: self-contained prose, no toolchain, no pin,
        # nothing of ours to fetch or run. The agent does the hoist in-context.
        app_dir, _ = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir)
        low = text.lower()
        for bad in CONFOUND:
            self.assertNotIn(bad.lower(), low, f"emitted skill leaked a confound: {bad!r}")
        self.assertIn("nothing of ours to fetch or run", text)

    def test_carries_the_recipe_inline_and_is_self_extracting(self):
        app_dir, config = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir)
        got = emit.extract_config(text)                 # recover from the one file
        self.assertEqual(got["app"], "toy")
        self.assertNotIn("operators", got)              # self-contained: no toolchain pin
        self.assertEqual(got, config)                   # the recipe, carried unchanged

    def test_is_deterministic(self):
        app_dir, _ = _toy_app_dir(self, "toy")
        self.assertEqual(emit.emit_skill(app_dir), emit.emit_skill(app_dir))

    def test_hermetic_app_declares_no_required_substrate(self):
        app_dir, _ = _toy_app_dir(self, "toy")
        text = emit.emit_skill(app_dir)
        self.assertIn("isolation substrate: none required", text)

    def test_extract_rejects_a_non_hoist_skill(self):
        with self.assertRaises(ValueError):
            emit.extract_config("---\nname: something-else\n---\n\njust prose\n")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_builder ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_builder")
    sys.exit(1)
