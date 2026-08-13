#!/usr/bin/env python3
"""Self-test for petard capability-card extraction. Hermetic, stdlib only."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "operators", "petard"))
import cards  # noqa: E402


class Cards(unittest.TestCase):

    def test_script_card_from_header(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "ensure-user.sh")
        with open(p, "w") as f:
            f.write("#!/usr/bin/env bash\n"
                    "# Create or update a realm user. Idempotent.\n"
                    "#\n"
                    "# Usage: ensure-user.sh <username> [password] [email]\n"
                    "set -euo pipefail\n")
        c = cards.extract_script_card(p)
        self.assertEqual(c["id"], "ensure-user")
        self.assertIn("realm user", c["purpose"])
        self.assertEqual(c["command"], "ensure-user.sh <username> [password] [email]")

    def test_makefile_cards_from_doc_comments(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "Makefile")
        with open(p, "w") as f:
            f.write("## Destroy all state including the databases. Not reversible.\n"
                    "nuke:\n\trm -rf state\n"
                    "\n"
                    "## The one bill.\n"
                    "spend:\n\techo bill\n")
        cs = cards.extract_makefile_cards(p)
        ids = {c["id"]: c for c in cs}
        self.assertIn("make-nuke", ids)
        self.assertIn("Destroy all state", ids["make-nuke"]["purpose"])
        self.assertEqual(ids["make-nuke"]["command"], "make nuke")
        self.assertEqual(ids["make-spend"]["command"], "make spend")

    def test_command_is_verbatim_from_ground_truth(self):
        # the whole point: a card's command is lifted from the file, never composed
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.sh")
        with open(p, "w") as f:
            f.write("#!/bin/sh\n# does a thing\n# Usage: x.sh --flag VALUE\ntrue\n")
        c = cards.extract_script_card(p)
        self.assertEqual(c["command"], "x.sh --flag VALUE")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_cards ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_cards")
    sys.exit(1)
