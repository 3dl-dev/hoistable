#!/usr/bin/env python3
"""Self-test for the app bundle builder. Stdlib only.

Two layers:
  - Hermetic (always): the bundle is a recipe, not a binary -- it pins the operators
    (does not vendor them), carries the LOM surface, and is deterministic.
  - Acceptance (docker-gated; asserts the honest cannot-build path when docker is
    absent, rather than skipping): the skillc envelope pattern proven end to end --
    build the operator kit, pack a bundle that pins it, LIFT the bundle out of the
    repo, and hoist it on a clean dind target. The bundle rebuilds the instance and
    the envelope self-grades it with an honest transfer score. Not write-and-run: a
    packed bundle actually hoists on a clean target and reports its score.
"""

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "release"))
sys.path.insert(0, os.path.join(HERE, "..", "core", "hoist"))
import build_bundle  # noqa: E402
import build_release  # noqa: E402
import hoist  # noqa: E402

HONCHO = os.path.join(HERE, "..", "examples", "honcho")


def _docker_ok():
    try:
        return subprocess.run("docker version", shell=True, capture_output=True,
                             timeout=20).returncode == 0
    except Exception:  # noqa: BLE001
        return False


HAS_DOCKER = _docker_ok()
PIN = {"version": "9.9.9", "url": "file:///tmp/does-not-resolve.tgz", "sha256": "x"}


class BundleShape(unittest.TestCase):

    def _members(self, tar_path):
        with tarfile.open(tar_path) as t:
            return {m.name: t.extractfile(m).read() for m in t.getmembers()}

    def test_pins_operators_and_does_not_vendor_them(self):
        out = tempfile.mkdtemp()
        tar_path, _ = build_bundle.build_bundle(HONCHO, PIN, out)
        members = self._members(tar_path)
        # the config carries the pin
        cfg = json.loads(members["config.json"])
        self.assertEqual(cfg["operators"], PIN)
        # ... and NOTHING of the operator kit is vendored into the bundle
        self.assertNotIn("envelope/envelope.py", members)
        self.assertFalse(any(n.endswith(".py") for n in members),
                        "a bundle vendors no operator code; it pins it")

    def test_carries_the_lom_surface(self):
        out = tempfile.mkdtemp()
        tar_path, _ = build_bundle.build_bundle(HONCHO, PIN, out)
        members = self._members(tar_path)
        self.assertIn("petard-cards-spec.json", members)   # LOM ground truth ships
        self.assertIn("MANIFEST.json", members)

    def test_is_deterministic(self):
        a = tempfile.mkdtemp()
        b = tempfile.mkdtemp()
        _, sha_a = build_bundle.build_bundle(HONCHO, PIN, a)
        _, sha_b = build_bundle.build_bundle(HONCHO, PIN, b)
        self.assertEqual(sha_a, sha_b)


class BundleAcceptance(unittest.TestCase):
    """The skillc pattern: a packed, lifted, self-pinning bundle hoists on a clean
    target and the envelope self-grades it honestly. Real dind."""

    def _toy_app(self):
        d = tempfile.mkdtemp(prefix="toy-app-")
        config = {
            "app": "toy",
            "binds": [{"name": "docker", "probe": "docker version", "required": True}],
            "default_profile": "minimal",
            "profiles": {"minimal": {
                "isolation": {"require": "environmental"},
                "bringup": [{"name": "up", "run": "echo up > marker"}],
                "health": [{"name": "marker", "check": "test -f marker"}],
                "acceptance": [{"name": "present", "check": "test -f marker"}],
            }},
        }
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump(config, f)
        with open(os.path.join(d, "petard-cards-spec.json"), "w") as f:
            json.dump({"helpcards": ['echo "Usage: toytool restart"']}, f)
        return d

    def test_packed_bundle_hoists_and_self_grades_on_a_clean_target(self):
        work = tempfile.mkdtemp(prefix="bundle-accept-")
        # cache the resolved kit somewhere disposable, not ~/.cache
        os.environ["HOIST_CACHE"] = os.path.join(work, "cache")

        # 1. build the operator kit release, to a local file:// artifact
        kit_path, kit_sha = build_release.build(
            "0.0.0-test", os.path.join(work, "dist"), ["envelope", "hoist", "operators"])
        pin = {"version": "0.0.0-test", "url": "file://" + kit_path, "sha256": kit_sha}

        # 2. pack a bundle for the toy app that PINS that kit
        bundle_path, _ = build_bundle.build_bundle(
            self._toy_app(), pin, os.path.join(work, "bundles"))

        # 3. LIFT the bundle out of the repo entirely
        lift = os.path.join(work, "lifted")
        os.makedirs(lift)
        with tarfile.open(bundle_path) as t:
            t.extractall(lift)
        lifted_config = os.path.join(lift, "config.json")
        self.assertTrue(os.path.isfile(lifted_config))

        # 4. hoist from the lifted bundle: it resolves the pin (fetch+verify the kit)
        #    and the envelope self-grades on the clean target.
        report = hoist.hoist(lifted_config, target_dir=os.path.join(work, "target"),
                            timeout=300, emit=lambda *a: None)

        if not HAS_DOCKER:
            self.assertEqual(report["outcome"], "cannot-build")
            return

        # the pin actually resolved: the kit was fetched and cached
        self.assertTrue(os.path.isfile(
            os.path.join(work, "cache", "0.0.0-test", ".resolved")),
            "the operator pin did not resolve")
        # the packed bundle rebuilt and self-graded honestly on the clean target
        self.assertEqual(report["outcome"], "built", report.get("did_not_transfer"))
        self.assertEqual(report["transfer"], [1, 1])
        self.assertEqual(report["substrate"]["strength"], "environmental")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_bundle ({result.testsRun} cases; "
              f"docker={'yes' if HAS_DOCKER else 'no'})")
        sys.exit(0)
    print("FAIL test_bundle")
    sys.exit(1)
