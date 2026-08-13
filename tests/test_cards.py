#!/usr/bin/env python3
"""Self-test for petard capability-card extraction. Hermetic, stdlib only."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "operators", "petard"))
import cards  # noqa: E402
import build_corpus  # noqa: E402


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


class HarvestThroughSubstrate(unittest.TestCase):
    """Contract C: the corpus is harvested THROUGH a resolved substrate handle, so
    it reflects the live deploy (dind / VM / cluster), never the host. The proof is
    that a command which would succeed on the HOST is NOT captured when the harvest
    is routed through an inside-the-substrate runner."""

    @staticmethod
    def _inside_run(cmd, timeout=60):
        # simulates exec INSIDE a substrate: it knows only the deploy's own tools,
        # and cannot see the host. 'echo HOSTSIDE' would trivially succeed on the
        # host; inside the substrate this stand-in does not resolve it.
        if "inside-tool" in cmd:
            return 0, "Usage: inside-tool restart <svc>\nRestart a service in place"
        return 127, "sh: not found (inside substrate)"

    def test_build_corpus_uses_the_injected_runner_not_the_host(self):
        sources = [
            {"name": "inside", "cmd": "inside-tool --help"},
            {"name": "host-marker", "cmd": "echo HOSTSIDE"},
        ]
        corpus = build_corpus.build_corpus(sources, run=self._inside_run)
        blob = "\n".join(e["text"] for e in corpus)
        self.assertIn("Restart a service", blob)          # harvested from inside
        self.assertNotIn("HOSTSIDE", blob)                # did NOT fall back to host
        marker = next(e for e in corpus if e["name"] == "host-marker")
        self.assertEqual(marker["rc"], 127)               # not resolvable inside

    def test_help_card_harvested_through_injected_runner(self):
        c = cards.extract_help_card("inside-tool --help", run=self._inside_run)
        self.assertEqual(c["command"], "inside-tool restart <svc>")
        self.assertIn("Restart", c["purpose"])
        # a command absent inside yields no card (petard does not fabricate one)
        self.assertIsNone(cards.extract_help_card("echo HOSTSIDE", run=self._inside_run))

    def test_substrate_runner_routes_to_sub_exec(self):
        class FakeSub:
            def __init__(self):
                self.calls = []
            def exec(self, cmd, cwd, env, timeout):
                self.calls.append((cmd, cwd))
                return 0, f"ran {cmd} in {cwd}"
        sub = FakeSub()
        run = build_corpus.substrate_runner(sub, "/work/honcho")
        rc, text = run("docker compose ps", 30)
        self.assertEqual(rc, 0)
        self.assertIn("/work/honcho", text)
        self.assertEqual(sub.calls, [("docker compose ps", "/work/honcho")])

    def test_default_harvest_still_runs_on_the_host(self):
        # back-compat: with no runner injected, harvest runs on the host.
        corpus = build_corpus.build_corpus([{"name": "e", "cmd": "echo HOSTSIDE"}])
        self.assertIn("HOSTSIDE", corpus[0]["text"])


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_cards ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_cards")
    sys.exit(1)
