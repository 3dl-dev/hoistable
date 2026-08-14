#!/usr/bin/env python3
"""arlo's grounding invariant. Hermetic, stdlib only.

Locks the two halves of the invariant: the corpus is generated from a command (not
authored), and answers are retrieval-grounded (every returned line exists in the
corpus). Carried from the operator's self-test; the invariant is the product.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from arlo import build_corpus  # noqa: E402

# A stand-in for a real `--help`: a command whose output is the ground truth.
FAKE_HELP = "printf '%s\\n' '--parent-id ID  attach to a parent' '--json  machine output'"


class Grounding(unittest.TestCase):

    def test_corpus_is_generated_with_provenance(self):
        corpus = build_corpus.build_corpus([{"name": "rd-help", "cmd": FAKE_HELP}])
        self.assertEqual(len(corpus), 1)
        entry = corpus[0]
        self.assertEqual(entry["source_cmd"], FAKE_HELP)  # provenance is the command
        self.assertIn("--parent-id", entry["text"])
        self.assertEqual(entry["rc"], 0)

    def test_answer_is_retrieval_grounded(self):
        corpus = build_corpus.build_corpus([{"name": "rd-help", "cmd": FAKE_HELP}])
        hits = build_corpus.answer(corpus, "parent-id")
        self.assertTrue(hits)
        self.assertIn("--parent-id", hits[0]["line"])
        self.assertEqual(hits[0]["from"], FAKE_HELP)
        corpus_text = "\n".join(e["text"] for e in corpus)
        for h in hits:  # every returned line is actually in the corpus, never synthesized
            self.assertIn(h["line"], corpus_text)

    def test_no_grounded_match_returns_nothing(self):
        corpus = build_corpus.build_corpus([{"name": "rd-help", "cmd": FAKE_HELP}])
        self.assertEqual(build_corpus.answer(corpus, "wombat-flag-xyz"), [])

    def test_asking_the_stale_name_surfaces_the_real_flag(self):
        # the --parent / --parent-id drift: ask the stale name, arlo hands back the
        # real one from the fresh corpus (a maintained doc would lie instead).
        corpus = build_corpus.build_corpus([{"name": "rd-help", "cmd": FAKE_HELP}])
        hits = build_corpus.answer(corpus, "--parent")
        self.assertTrue(any("--parent-id" in h["line"] for h in hits))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_grounding ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_grounding")
    sys.exit(1)
