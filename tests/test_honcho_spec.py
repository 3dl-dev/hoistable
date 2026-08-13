#!/usr/bin/env python3
"""Validate honcho's petard-cards spec: well-formed, and its sources are real
ground truth (real docker compose subcommands), never invented. Live card-building
against a running honcho is the honcho-loop test's job; this is the static check.

Run: python3 tests/test_honcho_spec.py
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "..", "examples", "honcho", "petard-cards-spec.json")

# The real docker compose subcommands an operator drives a stack with. A helpcard
# naming anything outside this set would be inventing a command, which petard's
# grounding invariant forbids.
COMPOSE_SUBCOMMANDS = {
    "up", "down", "restart", "start", "stop", "logs", "ps", "exec", "run",
    "kill", "pause", "unpause", "build", "pull", "create", "rm", "top", "events",
}


class HonchoSpec(unittest.TestCase):

    def setUp(self):
        with open(SPEC) as f:
            self.spec = json.load(f)

    def test_spec_is_well_formed(self):
        self.assertIsInstance(self.spec, dict)
        for key in ("scripts", "makefiles", "helpcards"):
            self.assertIsInstance(self.spec.get(key, []), list)
        self.assertTrue(self.spec["helpcards"], "no operational surface declared")

    def test_helpcards_are_real_compose_subcommands(self):
        for hc in self.spec["helpcards"]:
            self.assertTrue(hc.endswith("--help"),
                           f"{hc!r} is not a --help harvest")
            parts = hc.split()
            self.assertEqual(parts[:2], ["docker", "compose"],
                            f"{hc!r} is not a docker compose command")
            subcmd = parts[2]
            self.assertIn(subcmd, COMPOSE_SUBCOMMANDS,
                         f"{subcmd!r} is not a real docker compose subcommand "
                         "(a petard card must point at a real command, never an "
                         "invented one)")

    def test_bounce_and_logs_intents_are_covered(self):
        # the loop translates operator intent; the surface must carry the commands
        # those intents ground to.
        subcmds = {hc.split()[2] for hc in self.spec["helpcards"]}
        self.assertIn("restart", subcmds)   # "bounce honcho"
        self.assertIn("logs", subcmds)      # "show me the logs"


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_honcho_spec ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_honcho_spec")
    sys.exit(1)
