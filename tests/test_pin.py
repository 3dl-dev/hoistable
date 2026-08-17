#!/usr/bin/env python3
"""Enforce hoistable's adopt-by-pin of skillc. Every file hoistable vendors from skillc must
match the sha256 recorded in core/builder/skillc.pin. If someone edits a vendored copy here
instead of editing it in skillc and re-pinning, this test fails. That keeps skillc the single
source of truth for the cross-compile target profiles: adopt-by-pin, not fork-and-drift.

Run: python3 tests/test_pin.py
"""

import hashlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PIN = os.path.join(ROOT, "core", "builder", "skillc.pin")


class SkillcPin(unittest.TestCase):

    def setUp(self):
        with open(PIN) as f:
            self.pin = json.load(f)

    def test_pin_names_a_skillc_ref(self):
        self.assertRegex(self.pin.get("skillc_ref", ""), r"^[0-9a-f]{40}$",
                         "the pin must name a full skillc commit sha")

    def test_vendored_files_match_the_pinned_hash(self):
        adopted = self.pin.get("adopted", {})
        self.assertTrue(adopted, "the pin adopts nothing")
        for rel, meta in adopted.items():
            p = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(p), f"vendored file missing: {rel}")
            got = hashlib.sha256(open(p, "rb").read()).hexdigest()
            self.assertEqual(got, meta["sha256"],
                             f"{rel} drifted from the pin. Edit it in skillc and re-pin; "
                             "do not edit the vendored copy in hoistable.")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_pin ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_pin")
    sys.exit(1)
