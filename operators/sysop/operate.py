#!/usr/bin/env python3
"""sysop's operate driver: run the build -> run -> LOM loop as a thing you invoke.

The honcho loop is proven in a test, but a test is not a product. This is the
mechanical backbone that makes it runnable: deploy an app and KEEP IT RUNNING,
harvest petard's corpus from the LIVE deploy through the substrate handle (contract
C), answer operator intent with a grounded command, and tear down clean.

It is the seam hoistable owns -- the orchestration and glue (build-rule 6) -- not
agent judgment: it enforces the order (deploy, then harvest fresh, then always tear
down), and leaves discovery/authoring to the sysop SKILL that composes it. It writes
no command and invents nothing: every answer is a card harvested from the running
system, emitted verbatim (the petard invariant).

Standard library only; the local embedder is imported lazily behind the real
answerer, so this stays importable and testable without a model.
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "envelope"))
sys.path.insert(0, os.path.join(_HERE, "..", "petard"))
import envelope  # noqa: E402
import build_corpus  # noqa: E402
import cards  # noqa: E402
import translate  # noqa: E402


def operate_and_harvest(config, cards_spec=None, target_dir=None,
                       timeout=envelope.DEFAULT_TIMEOUT):
    """Deploy and grade the config, KEEP the substrate running, and harvest petard's
    cards from the live deploy through the substrate handle (contract C). Returns
    (report, substrate, cards). The substrate is LIVE -- ask() against the cards,
    then call substrate.teardown() when done. Cards are empty unless the deploy came
    up in an environmental substrate and a cards_spec was given."""
    report, sub = envelope.operate(config, target_dir, timeout=timeout)
    petard_cards = []
    if report.get("outcome") == "built" and cards_spec and sub.name != "host":
        workdir = report.get("workdir", sub.workroot())
        run = build_corpus.substrate_runner(sub, workdir)
        petard_cards = cards.build_cards(cards_spec, root=workdir, run=run)
    return report, sub, petard_cards


def answer(petard_cards, query, embed, floor=0.2):
    """Translate operator intent into a grounded command from the live deploy's
    cards. Returns the chosen card (with its verbatim command, confidence, and
    alternatives), or None below the confidence floor -- petard declines rather than
    guesses. `embed` is injected: the production embedder is petard's local
    sentence-transformer; tests pass a deterministic bag-of-words embedder."""
    if not petard_cards:
        return None
    hits = translate.rank(embed, petard_cards, query)
    if not hits or hits[0]["score"] < floor:
        return None
    return hits[0]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="sysop operate: deploy + keep running + petard-answer + teardown")
    ap.add_argument("config", help="a Layer 2 config JSON")
    ap.add_argument("--cards-spec", default=None,
                    help="a petard-cards spec to harvest the live deploy's surface")
    ap.add_argument("--ask", default=None,
                    help="an operator intent to translate to a grounded command")
    ap.add_argument("--keep", action="store_true",
                    help="leave the deploy running instead of tearing it down")
    ap.add_argument("--timeout", type=int, default=envelope.DEFAULT_TIMEOUT)
    ap.add_argument("--floor", type=float, default=0.2)
    args = ap.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)
    spec = None
    if args.cards_spec:
        with open(args.cards_spec) as f:
            spec = json.load(f)

    report, sub, petard_cards = operate_and_harvest(config, spec, timeout=args.timeout)
    print(envelope.format_report(report))
    if petard_cards:
        print(f"petard: harvested {len(petard_cards)} cards from the live deploy")
    try:
        if args.ask:
            if not petard_cards:
                print("petard: no live corpus to answer from.")
            else:
                embed = translate.sentence_transformer_embedder()
                hit = answer(petard_cards, args.ask, embed, floor=args.floor)
                if hit is None:
                    print(f"petard: no confident grounded match for {args.ask!r}. "
                          "It will not guess.")
                else:
                    print(f"RUN:  {hit['command']}")
                    print(f"      {hit['purpose'][:110]}")
                    print(f"      source: {hit['source']}   confidence {hit['score']}")
    finally:
        if args.keep:
            print(f"leaving the deploy running (substrate {sub.name}).")
        else:
            ok, _ = sub.teardown()
            residue = sub.residue()
            print(f"torn down (ok={ok}); host residue: {residue or 'clean'}")

    return {"built": 0, "feasible": 0, "honest-failure": 1,
            "cannot-build": 2}.get(report.get("outcome"), 3)


if __name__ == "__main__":
    sys.exit(main())
