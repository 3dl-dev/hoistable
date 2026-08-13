#!/usr/bin/env python3
"""Self-test for the hoist driver. Hermetic, stdlib only.

Proves hoist runs the two passes in order and returns the right outcome:
  - a feasible + passing config drives through to built
  - a config that fails preflight stops at the door and deploys nothing
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hoist"))
import hoist  # noqa: E402


def _write_config(config):
    fd, path = tempfile.mkstemp(prefix="hoist-cfg-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(config, f)
    return path


class HoistDriver(unittest.TestCase):

    def test_drives_preflight_then_deploy_to_built(self):
        cfg = _write_config({
            "app": "toy",
            "profiles": {"default": {
                "isolation": {"none": True, "why": "hermetic"},
                "bringup": [{"name": "up", "run": "echo up > .up"}],
                "health": [{"name": "m", "check": "test -f .up"}],
                "acceptance": [{"name": "a", "check": "true"}],
            }},
        })
        lines = []
        r = hoist.hoist(cfg, target_dir=tempfile.mkdtemp(), emit=lines.append)
        self.assertEqual(r["outcome"], "built")
        joined = "\n".join(lines)
        self.assertIn("[1/2] preflight", joined)
        self.assertIn("[2/2] deploy", joined)

    def test_stops_at_the_door_on_preflight_blocker(self):
        cfg = _write_config({
            "app": "toy",
            "binds": [{"name": "absent-xyz", "probe": "absent-xyz", "required": True}],
            "profiles": {"default": {
                "isolation": {"none": True, "why": "hermetic"},
                "bringup": [{"name": "up", "run": "echo up > .up"}],
                "acceptance": [{"name": "a", "check": "true"}],
            }},
        })
        d = tempfile.mkdtemp()
        lines = []
        r = hoist.hoist(cfg, target_dir=d, emit=lines.append)
        self.assertEqual(r["outcome"], "cannot-build")
        self.assertIn("stopped at the door", "\n".join(lines))
        # never deployed
        self.assertFalse(os.path.exists(os.path.join(d, ".up")))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_hoist ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_hoist")
    sys.exit(1)
