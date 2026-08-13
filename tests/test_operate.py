#!/usr/bin/env python3
"""Self-test for sysop's operate driver. Hermetic, stdlib only.

Proves the driver COMPOSES the loop correctly without real infra: it deploys and
keeps the substrate alive, harvests petard cards from the live deploy through the
substrate handle, answers grounded intent, and declines below the floor. The real
dind end-to-end drive is tests/test_honcho_loop.py.
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "envelope"))
sys.path.insert(0, os.path.join(HERE, "..", "operators", "petard"))
sys.path.insert(0, os.path.join(HERE, "..", "operators", "sysop"))
import substrate  # noqa: E402
import translate  # noqa: E402
import operate  # noqa: E402

# reuse the fake environmental substrate from the substrate test
sys.path.insert(0, os.path.join(HERE))
from test_substrate import FakeEnvSubstrate  # noqa: E402


CARDS = [
    {"id": "compose-restart", "command": "docker compose restart [SERVICE...]",
     "purpose": "restart service containers", "source": "docker compose restart --help"},
    {"id": "compose-logs", "command": "docker compose logs [SERVICE...]",
     "purpose": "view output from containers", "source": "docker compose logs --help"},
]
VOCAB = {"restart", "service", "services", "logs", "view", "output", "containers",
         "docker", "compose", "show", "bounce", "xyzzy"}


class Answer(unittest.TestCase):

    def setUp(self):
        self.embed = translate.bag_of_words_embedder(VOCAB)

    def test_grounds_intent_to_a_real_card_command(self):
        hit = operate.answer(CARDS, "restart the services", self.embed)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["command"], "docker compose restart [SERVICE...]")

    def test_declines_below_the_floor_rather_than_guessing(self):
        self.assertIsNone(operate.answer(CARDS, "xyzzy nothing here", self.embed))

    def test_no_cards_declines(self):
        self.assertIsNone(operate.answer([], "restart", self.embed))


class OperateAndHarvest(unittest.TestCase):
    """The driver keeps the deploy up and harvests cards from it through the handle,
    all without real infra (a fake environmental substrate stands in for dind)."""

    def setUp(self):
        self.fake = FakeEnvSubstrate()
        self._saved = substrate.ENVIRONMENTAL_LADDER
        substrate.ENVIRONMENTAL_LADDER = [
            ("fake-env", "environmental", "true", lambda c, t: self.fake)]

    def tearDown(self):
        substrate.ENVIRONMENTAL_LADDER = self._saved

    def test_operate_keeps_up_harvests_through_handle_and_answers(self):
        config = {"app": "toy", "profiles": {"default": {
            "isolation": {"require": "environmental"},
            "bringup": [{"name": "up", "run": "true"}],
            "health": [{"name": "h", "check": "true"}],
            "acceptance": [{"name": "a", "check": "true"}],
        }}}
        # a helpcard that harvests cleanly inside the fake substrate's shell
        spec = {"helpcards": ['echo "Usage: mytool restart <svc>"']}

        report, sub, cards = operate.operate_and_harvest(config, spec)
        try:
            self.assertEqual(report["outcome"], "built")
            self.assertFalse(self.fake.torn_down)          # kept running
            self.assertIs(sub, self.fake)
            # harvested through the substrate handle (the helpcard ran via sub.exec)
            self.assertTrue(cards, "no cards harvested from the live deploy")
            self.assertTrue(any("mytool restart" in c["command"] for c in cards))
            self.assertTrue(any('echo "Usage: mytool restart <svc>"' in c
                               for c in self.fake.exec_calls))
            # and the driver answers grounded intent from that live corpus
            embed = translate.bag_of_words_embedder(
                {"restart", "svc", "mytool", "service"})
            hit = operate.answer(cards, "restart the svc", embed)
            self.assertIsNotNone(hit)
            self.assertIn("mytool restart", hit["command"])
        finally:
            sub.teardown()
        self.assertTrue(self.fake.torn_down)               # explicit teardown


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_operate ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_operate")
    sys.exit(1)
