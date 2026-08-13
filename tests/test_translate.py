#!/usr/bin/env python3
"""Self-test for petard's translation layer. Hermetic, stdlib only.

Uses a deterministic bag-of-words embedder (no model download) to lock the two
properties that matter: the translator selects the right card, and it can ONLY
ever return a command that exists in the cards (grounded by construction).
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "operators", "petard"))
import translate  # noqa: E402

CARDS = [
    {"id": "ensure-user", "command": "ensure-user.sh <username> [password]",
     "purpose": "create or update a realm user set the password", "source": "bin/ensure-user.sh"},
    {"id": "make-nuke", "command": "make nuke",
     "purpose": "destroy all state including the databases", "source": "Makefile:nuke"},
    {"id": "compose-restart", "command": "docker compose restart [SERVICE...]",
     "purpose": "restart service containers", "source": "docker compose restart --help"},
]
VOCAB = set(w for c in CARDS for w in (c["purpose"] + " " + c["command"]).lower()
            .replace("/", " ").replace("-", " ").split())


class Translate(unittest.TestCase):

    def setUp(self):
        self.embed = translate.bag_of_words_embedder(VOCAB | {"reset", "restart", "wipe"})

    def test_selects_the_matching_card(self):
        hits = translate.rank(self.embed, CARDS, "set password", top=3)
        self.assertEqual(hits[0]["id"], "ensure-user")

    def test_restart_maps_to_restart_card(self):
        hits = translate.rank(self.embed, CARDS, "restart service", top=3)
        self.assertEqual(hits[0]["id"], "compose-restart")

    def test_only_ever_returns_a_real_card_command(self):
        # grounded by construction: whatever the query, the command is a card's
        real = {c["command"] for c in CARDS}
        for q in ["reset password", "wipe everything", "restart containers", "asdf qwer"]:
            for h in translate.rank(self.embed, CARDS, q, top=3):
                self.assertIn(h["command"], real)

    def test_no_match_scores_stay_low(self):
        # a query sharing no vocabulary scores ~0, so the CLI floor refuses it
        hits = translate.rank(self.embed, CARDS, "xyzzy plugh", top=1)
        self.assertLess(hits[0]["score"], 0.2)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_translate ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_translate")
    sys.exit(1)
