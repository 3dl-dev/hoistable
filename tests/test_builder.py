#!/usr/bin/env python3
"""Self-test for the hoist builder (use case 1): emit an app as a self-building
distributable hoist SKILL, and grade the whole stack. Stdlib only.

Two layers:
  - Emit shape (always, hermetic): the emitted file is one self-building skill — it
    stamps the receiver-side hoist recipe verbatim, carries the app's recipe inlined and
    self-pinning, declares binds/checks/acceptance, and is deterministic. It is
    self-extracting: extract_config recovers the carried recipe from the one file.
  - Whole-stack grade (ground-source, never skips — a hermetic app, so no docker): the
    loss function over the ENTIRE stack. Build a real operator kit release, emit a skill
    that PINS it, LIFT the carried recipe out, and hoist it: the skill self-extracts the
    verified harness and the envelope self-grades on a clean target to BUILT with an
    honest transfer score. Not write-and-run: the emitted skill actually hoists.

Run: python3 tests/test_builder.py
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "builder"))
sys.path.insert(0, os.path.join(HERE, "..", "release"))
sys.path.insert(0, os.path.join(HERE, "..", "hoist"))
import emit  # noqa: E402
import build_release  # noqa: E402
import hoist  # noqa: E402

FAKE_PIN = {"version": "1.2.3", "url": "file:///nope.tgz", "sha256": "deadbeef"}


def _toy_app_dir(name="toy"):
    """A hermetic toy app: isolation none, bringup writes a marker in its throwaway
    target, acceptance checks it. No docker, no source clone — free to grade."""
    d = tempfile.mkdtemp(prefix=f"builder-{name}-")
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

    def test_emits_one_self_building_skill_with_the_recipe_stamped(self):
        app_dir, _ = _toy_app_dir("toy")
        text = emit.emit_skill(app_dir, FAKE_PIN)
        self.assertTrue(text.startswith("---\nname: hoist-toy\n"))
        # the receiver-side recipe is stamped verbatim, with <app> resolved
        self.assertIn("This skill hoists toy before it reports toy is up", text)
        self.assertIn("## Hoist recipe (run before your first report that toy is up)", text)
        self.assertIn("self-extract the harness", text.lower())
        # binds, checks, acceptance all present
        self.assertIn("## Binds", text)
        self.assertIn("## Checks", text)
        self.assertIn("## Acceptance", text)
        self.assertIn("`marker-present`", text)

    def test_carries_the_recipe_self_pinning_and_is_self_extracting(self):
        app_dir, config = _toy_app_dir("toy")
        text = emit.emit_skill(app_dir, FAKE_PIN)
        got = emit.extract_config(text)                 # recover from the one file
        self.assertEqual(got["app"], "toy")
        self.assertEqual(got["operators"], FAKE_PIN)    # self-pinning
        # the carried recipe is the app's recipe, unchanged but for the injected pin
        expect = dict(config, operators=FAKE_PIN)
        self.assertEqual(got, expect)

    def test_is_deterministic(self):
        app_dir, _ = _toy_app_dir("toy")
        self.assertEqual(emit.emit_skill(app_dir, FAKE_PIN),
                        emit.emit_skill(app_dir, FAKE_PIN))

    def test_hermetic_app_declares_no_required_substrate(self):
        app_dir, _ = _toy_app_dir("toy")
        text = emit.emit_skill(app_dir, FAKE_PIN)
        self.assertIn("isolation substrate: none required", text)

    def test_extract_rejects_a_non_hoist_skill(self):
        with self.assertRaises(ValueError):
            emit.extract_config("---\nname: something-else\n---\n\njust prose\n")

    def test_pin_for_kit_derives_a_resolvable_pin(self):
        # the tower surfaced this: a pin must resolve, not point at a not-yet-published
        # URL. Derive it from the kit that exists.
        import hashlib as _h
        d = tempfile.mkdtemp(prefix="builder-kit-")
        kit = os.path.join(d, "hoistable-operators-9.9.9.tgz")
        with open(kit, "wb") as f:
            f.write(b"kit-bytes")
        pin = emit.pin_for_kit(kit)
        self.assertEqual(pin["version"], "9.9.9")                 # from the filename
        self.assertEqual(pin["sha256"], _h.sha256(b"kit-bytes").hexdigest())
        self.assertEqual(pin["url"], "file://" + kit)            # resolves (local)
        # a published URL overrides the file:// default
        self.assertEqual(emit.pin_for_kit(kit, url="https://x/y.tgz")["url"],
                        "https://x/y.tgz")


class WholeStackGrade(unittest.TestCase):
    """The loss function over the entire stack: emit -> self-extract the pinned harness
    -> deploy -> grade. Hermetic app, so this runs for free and never skips."""

    def test_emitted_skill_self_extracts_and_hoists_to_built(self):
        work = tempfile.mkdtemp(prefix="builder-stack-")
        os.environ["HOIST_CACHE"] = os.path.join(work, "cache")

        # 1. a real operator kit release, to a local file:// artifact
        kit_path, kit_sha = build_release.build(
            "0.0.0-test", os.path.join(work, "dist"), ["envelope", "hoist", "operators"])
        # derive the pin from the kit that exists (the tower's optimization) -- one step,
        # and it resolves; the derived hash must match what the build produced
        pin = emit.pin_for_kit(kit_path)
        self.assertEqual(pin["sha256"], kit_sha)
        self.assertTrue(pin["url"].startswith("file://"))

        # 2. emit the toy app's distributable skill, PINNING that kit
        app_dir, _ = _toy_app_dir("toy")
        skill_text = emit.emit_skill(app_dir, pin)
        skill_path = os.path.join(work, "toy.hoist.SKILL.md")
        with open(skill_path, "w") as f:
            f.write(skill_text)

        # 3. self-extract: recover the carried recipe from the one skill file, LIFTED
        #    entirely out of the app dir (proves the skill is self-contained)
        with open(skill_path) as f:
            lifted = emit.extract_config(f.read())
        lifted_cfg = os.path.join(work, "lifted-config.json")
        with open(lifted_cfg, "w") as f:
            json.dump(lifted, f)

        # 4. hoist it: the pin resolves (fetch+verify the kit), the envelope self-grades
        report = hoist.hoist(lifted_cfg, target_dir=os.path.join(work, "target"),
                            timeout=120, emit=lambda *a: None)

        # the harness self-extracted: the pinned kit was fetched, verified, and cached
        self.assertTrue(os.path.isfile(
            os.path.join(work, "cache", "0.0.0-test", ".resolved")),
            "the operator pin did not resolve (harness did not self-extract)")
        # the whole stack graded green: BUILT, honest transfer 2 of 2
        self.assertEqual(report["outcome"], "built", report.get("did_not_transfer"))
        self.assertEqual(report["transfer"], [2, 2])


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_builder ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_builder")
    sys.exit(1)
