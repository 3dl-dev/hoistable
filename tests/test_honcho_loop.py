#!/usr/bin/env python3
"""The build -> run -> LOM loop, closed on honcho, end to end and for real.

honcho already hoists to BUILT inside dind. This proves the run -> LOM half:

  (a) honcho is deployed into dind and KEPT RUNNING (OPERATE mode), not torn down.
  (b) petard harvests honcho's command surface THROUGH the substrate handle
      (contract C) -- cards built from the LIVE deploy, with no host access.
  (c) a petard translate query returns a REAL grounded honcho command from those
      cards (verbatim), and nonsense is declined rather than invented.
  (d) the host is left clean: the substrate leaves no residue.
  (e) the substrate is explicitly torn down.

This is the LOM leg, which the prior-art survey found has no prior art. It runs
against REAL dind, not a mock. When docker does not resolve on the target, the
same test asserts the honest cannot-build path instead of skipping.

Run: python3 tests/test_honcho_loop.py    (needs docker; ~2-3 min: cold build in dind)
"""

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "envelope"))
sys.path.insert(0, os.path.join(HERE, "..", "operators", "petard"))
import envelope  # noqa: E402
import cards  # noqa: E402
import build_corpus  # noqa: E402
import translate  # noqa: E402

CONFIG = os.path.join(HERE, "..", "examples", "honcho", "config.json")
SPEC = os.path.join(HERE, "..", "examples", "honcho", "petard-cards-spec.json")


def _load(path):
    with open(path) as f:
        return json.load(f)


def _docker_ok():
    try:
        return subprocess.run("docker version", shell=True, capture_output=True,
                             timeout=20).returncode == 0
    except Exception:  # noqa: BLE001
        return False


HAS_DOCKER = _docker_ok()


class HonchoLoop(unittest.TestCase):

    def test_build_run_lom_closed_end_to_end(self):
        config = _load(CONFIG)

        if not HAS_DOCKER:
            # honcho requires an environmental substrate; with no docker none
            # resolves, so operate reports cannot-build and keeps nothing up.
            report, sub = envelope.operate(config)
            self.assertEqual(report["outcome"], "cannot-build")
            self.assertIn("no isolation substrate", report["reason"])
            return

        report, sub = envelope.operate(config, timeout=1200)
        try:
            # (a) built and KEPT RUNNING inside dind
            self.assertEqual(report["outcome"], "built",
                            report.get("did_not_transfer"))
            self.assertEqual(report["substrate"]["strength"], "environmental")
            self.assertTrue(report["substrate"].get("operating"))
            workdir = report["workdir"]                     # /work/honcho, in-container
            self.assertFalse(os.path.exists(workdir),
                            "the deploy should live inside the substrate, not the host")
            # the api is genuinely up inside: hit its health endpoint through the handle
            rc, out = sub.exec("curl -fsS http://localhost:8000/health", workdir, {}, 30)
            self.assertEqual(rc, 0, f"honcho api not live inside the substrate: {out}")

            # (b) harvest honcho's command surface THROUGH the substrate handle
            spec = _load(SPEC)
            run = build_corpus.substrate_runner(sub, workdir)
            honcho_cards = cards.build_cards(spec, root=workdir, run=run)
            self.assertTrue(honcho_cards, "no cards harvested from inside the deploy")
            # real honcho operational commands, harvested live from the running stack
            cmds = " ".join(c["command"].lower() for c in honcho_cards)
            self.assertIn("restart", cmds)
            self.assertIn("logs", cmds)
            for c in honcho_cards:                          # all from the live compose
                self.assertIn("compose", c["command"].lower())

            # (c) translate operator intent -> a REAL grounded honcho command
            vocab = {"restart", "bounce", "logs", "show", "services", "tail",
                     "container", "containers"}
            for c in honcho_cards:
                vocab |= set((c["purpose"] + " " + c["command"]).lower()
                             .replace("/", " ").replace("-", " ").split())
            embed = translate.bag_of_words_embedder(vocab)
            real_cmds = {c["command"] for c in honcho_cards}

            hits = translate.rank(embed, honcho_cards, "restart the services", top=3)
            self.assertTrue(hits)
            self.assertIn("restart", hits[0]["command"].lower())
            self.assertIn(hits[0]["command"], real_cmds)    # verbatim, never invented

            hits = translate.rank(embed, honcho_cards, "show me the logs", top=3)
            self.assertIn("logs", hits[0]["command"].lower())
            self.assertIn(hits[0]["command"], real_cmds)

            # refuses to invent: nonsense stays below the confidence floor
            nonsense = translate.rank(embed, honcho_cards, "xyzzy plugh frobnicate", top=1)
            self.assertLess(nonsense[0]["score"], 0.2)
        finally:
            # (e) explicit teardown; (d) host left clean, no residue of ours
            ok, _ = sub.teardown()
            self.assertTrue(ok)
            self.assertEqual(sub.residue(), [],
                            "the substrate left residue on the host after teardown")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_honcho_loop ({result.testsRun} case; "
              f"docker={'yes' if HAS_DOCKER else 'no'})")
        sys.exit(0)
    print("FAIL test_honcho_loop")
    sys.exit(1)
