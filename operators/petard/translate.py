#!/usr/bin/env python3
"""petard's grounded translation layer: intent -> the command to run.

This is the half that makes petard more than a list of commands. It takes the
operator's own words ("bounce the workshop instances", "reset a password") and
returns the command to run, when the frontier is down and credits are out.

How it stays grounded while still bridging vocabulary:

  - The candidates are capability CARDS (cards.py), each a real command paired
    with its ground-truth purpose. The model NEVER writes a command. It only
    SELECTS a card by semantic similarity between the query and the card's
    purpose, and the card's command is emitted verbatim from ground truth. So
    petard cannot invent a command; the worst it can do is pick the wrong real
    one, and it shows its confidence and the alternatives so the operator can
    tell.

  - The embedder is frontier-independent: a small local model provisioned at
    setup time (see provision). If confidence is below a floor, petard says it
    has no confident match rather than guessing.

The embedder is pluggable so the grounding is testable without any model: rank()
takes an embed function. The production embedder is a local sentence-transformer;
the test embedder is a deterministic bag-of-words. Standard library only here;
the model dependency lives behind the production embedder.
"""

import argparse
import json
import math
import sys


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _stems(s):
    """Crude morphological tokens: lowercased, punctuation split, 5-char prefix.
    Bridges instances/instance and workshop/workspace without a synonym list."""
    raw = (s.lower().replace("/", " ").replace("-", " ")
           .replace("[", " ").replace("]", " ").replace("<", " ").replace(">", " ")
           .replace(".", " ").replace(",", " ").replace("(", " ").replace(")", " ").split())
    return {w[:5] for w in raw if len(w) > 2}


def _lexical(query, text):
    """Fraction of query stems present in the card text. The exact-term anchor
    that keeps semantic drift (reset~reload, password~credentials) from winning."""
    qs = _stems(query)
    if not qs:
        return 0.0
    return len(qs & _stems(text)) / len(qs)


def rank(embed, cards, query, top=3, w_purpose_lex=0.4, w_command_lex=0.8):
    """embed: fn(list[str]) -> list[normalized vector]. Ranks cards by a hybrid of
    semantic similarity (bridges vocabulary) and lexical stem overlap (anchors on
    the operator's actual terms). The command signature is weighted higher than
    prose: a flag or arg named in the command (a literal [password]) is a stronger
    signal than a word in the description. Every returned command is a card's
    command, verbatim: the score only chooses which real command to surface,
    never writes one."""
    texts = [f"{c['purpose']} {c['command']}" for c in cards]
    vecs = embed(texts)
    qv = embed([query])[0]

    def score(i):
        c = cards[i]
        return (_dot(qv, vecs[i])
                + w_purpose_lex * _lexical(query, c["purpose"])
                + w_command_lex * _lexical(query, c["command"]))

    order = sorted(range(len(cards)), key=lambda i: -score(i))[:top]
    return [{
        "score": round(score(i), 4),
        "id": cards[i]["id"],
        "command": cards[i]["command"],
        "purpose": cards[i]["purpose"],
        "source": cards[i]["source"],
    } for i in order]


def sentence_transformer_embedder(model_name="all-MiniLM-L6-v2"):
    """The frontier-independent local embedder. Imported lazily so this module
    stays importable (and testable) without the model installed."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)

    def embed(texts):
        rows = model.encode(texts, normalize_embeddings=True)
        return [[float(x) for x in row] for row in rows]

    return embed


def bag_of_words_embedder(vocab):
    """A deterministic, model-free embedder for tests: a normalized indicator
    vector over a fixed vocabulary. No semantics, but enough to prove grounding
    and ranking mechanics without downloading a model."""
    vocab = list(vocab)

    def embed(texts):
        out = []
        for t in texts:
            toks = set(t.lower().replace("/", " ").replace("-", " ").split())
            v = [1.0 if w in toks else 0.0 for w in vocab]
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

    return embed


def main(argv=None):
    ap = argparse.ArgumentParser(description="petard: translate intent to a grounded command")
    ap.add_argument("cards", help="a cards.json from cards.py")
    ap.add_argument("query", nargs="+")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--floor", type=float, default=0.2,
                    help="below this confidence, petard says it has no match rather than guess")
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    args = ap.parse_args(argv)

    with open(args.cards) as f:
        cards = json.load(f)
    embed = sentence_transformer_embedder(args.model)
    hits = rank(embed, cards, " ".join(args.query), args.top)

    if not hits or hits[0]["score"] < args.floor:
        print("petard: no confident grounded match. It will not guess.")
        if hits:
            print(f"  (closest was {hits[0]['id']} at {hits[0]['score']}; sysop may need to "
                  "harvest a runbook entry for this task -- contract C.)")
        return 1

    best = hits[0]
    print(f"RUN:  {best['command']}")
    print(f"      {best['purpose'][:110]}")
    print(f"      source: {best['source']}   confidence {best['score']}")
    if len(hits) > 1:
        print("also consider:")
        for h in hits[1:]:
            print(f"  - {h['command']}   ({h['score']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
