#!/usr/bin/env python3
"""arlo standalone, graded on the host with no frontier and no model download.

Two things the spike must prove for real:

  1. HOST-RUN PATH: arlo harvests a card from real ground truth on this box (a
     script's Usage: line, and a real command's own --help via _host_run), then
     translates a query into that card's command verbatim. No injected
     environment, no frontier: the plain standalone host path.

  2. RUNG 1 (slot-fill): the binder fills a real card template's hole from intent,
     and the command SKELETON is never altered, structurally, not on trust. Even a
     binder that returns a full command or a shell-injection value cannot change the
     command shape.

Hermetic: the embedder is arlo's deterministic bag-of-words (translate), the binder
is arlo's deterministic residual_binder (binder). Both are genuine, model-free
implementations, not mocks; they prove the mechanics without a model. `ls --help` is
real coreutils ground truth present on the box.
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from arlo import cards, translate, binder  # noqa: E402

SCRIPT = """#!/usr/bin/env bash
# Restart the workshop instances after a config change.
# Usage: bounce-workshop [instance]
echo restarting "$1"
"""


class HostRunPath(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="arlo-spike-")
        with open(os.path.join(self.root, "bounce-workshop.sh"), "w") as f:
            f.write(SCRIPT)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_harvest_and_translate_on_the_host(self):
        # cards from real ground truth: a script on disk + a real command's --help
        # harvested through _host_run (the default host runner, no environment).
        spec = {"scripts": ["bounce-workshop.sh"], "makefiles": [], "helpcards": ["ls --help"]}
        cs = cards.build_cards(spec, root=self.root)
        ids = {c["id"] for c in cs}
        self.assertIn("bounce-workshop", ids)  # script card harvested
        self.assertIn("ls", ids)               # real --help harvested via host subprocess

        # every card's command came from ground truth (a Usage line or a --help
        # synopsis), never authored.
        bounce = next(c for c in cs if c["id"] == "bounce-workshop")
        self.assertEqual(bounce["command"], "bounce-workshop [instance]")

        # translate a query with arlo's deterministic embedder: it must return a
        # real card's command verbatim, never a synthesized one.
        embed = translate.bag_of_words_embedder(
            {"restart", "workshop", "instances", "bounce", "list", "directory", "ls", "file"})
        hits = translate.rank(embed, cs, "restart the workshop instances")
        self.assertTrue(hits)
        commands = {c["command"] for c in cs}
        self.assertIn(hits[0]["command"], commands)          # grounded: it is a real card
        self.assertEqual(hits[0]["command"], bounce["command"])

    def test_absent_command_yields_no_fabricated_card(self):
        # a --help for a command that does not exist runs, fails, and yields nothing,
        # rather than a card pointing at a command that is not there.
        spec = {"scripts": [], "makefiles": [], "helpcards": ["arlo-nonexistent-xyz --help"]}
        cs = cards.build_cards(spec, root=self.root)
        self.assertEqual(cs, [])


CARD = {"command": "docker compose restart [service]",
        "purpose": "restart a service in the running stack",
        "source": "docker compose restart --help"}


class Rung1SlotFill(unittest.TestCase):

    def test_binds_the_hole_from_intent(self):
        res = binder.slot_fill(binder.residual_binder, CARD, "bounce the deriver")
        self.assertEqual(res["bindings"], {"service": "deriver"})
        self.assertEqual(res["command"], "docker compose restart deriver")
        self.assertTrue(res["skeleton_preserved"])
        # structural: template = prefix + [service] + suffix; filled = prefix + value + suffix.
        pre, post = CARD["command"].split("[service]")
        self.assertTrue(res["command"].startswith(pre))
        self.assertTrue(res["command"].endswith(post.rstrip()) or res["command"].endswith(post))

    def test_does_not_guess_when_no_residual(self):
        # every query word is already accounted for by the card: nothing to bind.
        res = binder.slot_fill(binder.residual_binder, CARD, "restart a service")
        self.assertEqual(res["bindings"], {})
        self.assertIn("service", res["unbound"])
        self.assertEqual(res["command"], CARD["command"])  # placeholder left for the operator
        self.assertTrue(res["skeleton_preserved"])

    def test_no_slots_means_untouched(self):
        card = {"command": "docker compose ps", "purpose": "show status", "source": "x"}
        res = binder.slot_fill(binder.residual_binder, card, "what is running")
        self.assertEqual(res["command"], "docker compose ps")
        self.assertEqual(res["bindings"], {})

    def test_binder_cannot_return_a_command(self):
        # a binder (or a hallucinating model) that returns a full command instead of
        # slot values changes nothing: only slot VALUES are honored, and the command
        # is assembled from the real template.
        rogue = binder.llm_binder(lambda prompt: "rm -rf /")   # not JSON, no slot values
        res = binder.slot_fill(rogue, CARD, "bounce the deriver")
        self.assertEqual(res["command"], CARD["command"])      # untouched
        self.assertNotIn("rm -rf", res["command"])
        self.assertTrue(res["skeleton_preserved"])

    def test_slot_value_cannot_chain_a_second_command(self):
        # the model supplies a value that smuggles shell metacharacters: it is
        # refused, the slot stays unbound, and no second command is chained in.
        rogue = binder.llm_binder(lambda prompt: '{"service": "api; rm -rf /"}')
        res = binder.slot_fill(rogue, CARD, "bounce the api")
        self.assertNotIn("rm -rf", res["command"])
        self.assertIn("service", res["unbound"])
        self.assertTrue(res["skeleton_preserved"])

    def test_wellbehaved_model_binds_the_value(self):
        good = binder.llm_binder(lambda prompt: 'the answer is {"service": "api"}')
        res = binder.slot_fill(good, CARD, "bounce the api")
        self.assertEqual(res["command"], "docker compose restart api")
        self.assertTrue(res["skeleton_preserved"])


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_host_translate ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_host_translate")
    sys.exit(1)
