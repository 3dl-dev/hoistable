#!/usr/bin/env python3
"""Self-test for the envelope runner. Stdlib only, hermetic, deterministic.

Proves the three outcomes on toy configs that need no network and no app:
  - cannot-build  (a required bind is absent)
  - honest-failure (it comes up but an acceptance check fails)
  - built          (up and everything passes)

Run: python3 tests/test_envelope.py   -> prints PASS and exits 0, or fails loud.
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "envelope"))
import envelope  # noqa: E402


def _target():
    return tempfile.mkdtemp(prefix="hoist-test-")


class EnvelopeOutcomes(unittest.TestCase):

    def test_cannot_build_names_missing_bind(self):
        config = {
            "app": "toy",
            "binds": [
                {"name": "definitely-absent-binary-xyz",
                 "probe": "definitely-absent-binary-xyz --version", "required": True},
            ],
            "profiles": {"default": {"acceptance": [{"name": "x", "check": "true"}]}},
        }
        r = envelope.run_envelope(config, _target())
        self.assertEqual(r["outcome"], "cannot-build")
        self.assertIn("definitely-absent-binary-xyz", r["reason"])
        # never ran acceptance: it stopped at the door
        self.assertEqual(r["acceptance"], [])

    def test_cannot_build_on_preflight_blocker(self):
        config = {
            "app": "toy",
            "profiles": {"default": {
                "preflight": [{"name": "needs-impossible", "probe": "false", "required": True}],
                "acceptance": [{"name": "x", "check": "true"}],
            }},
        }
        r = envelope.run_envelope(config, _target())
        self.assertEqual(r["outcome"], "cannot-build")
        self.assertIn("preflight blocker", r["reason"])

    def test_honest_failure_says_what_did_not_transfer(self):
        config = {
            "app": "toy",
            "profiles": {"default": {
                "isolation": {"none": True, "why": "hermetic toy test"},
                "bringup": [{"name": "up", "run": "echo up > .up"}],
                "health": [{"name": "marker", "check": "test -f .up"}],
                "acceptance": [
                    {"name": "passes", "check": "true"},
                    {"name": "fails", "check": "false"},
                ],
            }},
        }
        r = envelope.run_envelope(config, _target())
        self.assertEqual(r["outcome"], "honest-failure")
        self.assertEqual(r["transfer"], [1, 2])
        self.assertEqual(r["transfer_score"], 0.5)
        self.assertIn("acceptance:fails", r["did_not_transfer"])

    def test_honest_failure_when_it_does_not_come_up(self):
        config = {
            "app": "toy",
            "profiles": {"default": {
                "isolation": {"none": True, "why": "hermetic toy test"},
                "bringup": [{"name": "up", "run": "true"}],
                "health": [{"name": "missing", "check": "test -f .never-created"}],
                "acceptance": [{"name": "x", "check": "true"}],
            }},
        }
        r = envelope.run_envelope(config, _target())
        self.assertEqual(r["outcome"], "honest-failure")
        # acceptance is not run when the install gate is down
        self.assertEqual(r["acceptance"], [])
        self.assertIn("health:missing", r["did_not_transfer"])

    def test_built_when_everything_passes(self):
        config = {
            "app": "toy",
            "profiles": {"default": {
                "isolation": {"none": True, "why": "hermetic toy test"},
                "bringup": [{"name": "up", "run": "echo up > .up"}],
                "health": [{"name": "marker", "check": "test -f .up"}],
                "acceptance": [
                    {"name": "a", "check": "true"},
                    {"name": "b", "check": "test -f .up"},
                ],
            }},
        }
        r = envelope.run_envelope(config, _target())
        self.assertEqual(r["outcome"], "built")
        self.assertEqual(r["transfer_score"], 1.0)
        self.assertEqual(r["did_not_transfer"], [])

    def test_refuses_bringup_without_isolation(self):
        # The non-destructive onboarding invariant: a deploying profile that
        # declares no isolation is rejected, never run.
        config = {
            "app": "toy",
            "profiles": {"default": {
                "bringup": [{"name": "up", "run": "true"}],
                "acceptance": [{"name": "x", "check": "true"}],
            }},
        }
        r = envelope.run_envelope(config, _target())
        self.assertEqual(r["outcome"], "cannot-build")
        self.assertIn("isolation", r["reason"])
        self.assertEqual(r["bringup"], [])  # never deployed

    def test_isolation_injects_namespace_and_tears_down(self):
        d = _target()
        config = {
            "app": "toy",
            "profiles": {"default": {
                "isolation": {
                    "namespace_env": "MYNS",
                    "port_envs": ["MYPORT"],
                    "collision_probe": "true",
                    "teardown": "rm -f ns-marker",
                },
                "bringup": [{"name": "up", "run": "echo $MYNS > ns-marker"}],
                "health": [{"name": "marker", "check": "test -f ns-marker"}],
                "acceptance": [{"name": "ns-used", "check": "grep -q hoist-toy- ns-marker"}],
            }},
        }
        r = envelope.run_envelope(config, d)
        self.assertEqual(r["outcome"], "built")
        self.assertTrue(r["isolation"]["namespace"].startswith("hoist-toy-"))
        self.assertIsInstance(r["isolation"]["ports"]["MYPORT"], int)
        self.assertTrue(r["teardown"]["ok"])
        # teardown removed the marker: the target is left as it was found
        self.assertFalse(os.path.exists(os.path.join(d, "ns-marker")))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_envelope ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_envelope")
    sys.exit(1)
