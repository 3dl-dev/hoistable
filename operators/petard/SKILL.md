---
name: petard
description: The no-frontier operational fallback. Translates the operator's own words into the exact command to run, grounded in the system's own ground truth, when the frontier stack is down and credits are out. Never invents a command.
---

petard keeps you able to operate when the frontier model is down or rate limited.
The bar it must clear: you type your own words ("bounce the workshop instances",
"reset a password", "restart"), and it hands back the command to run. A pile of docs
nobody reads at 3am is not a petard. It is not autonomous ops and not a smart model;
it runs on independent power and network. If it depends on the thing that is down, it
is not a petard.

It has three parts, and the honesty comes from keeping them separate: the model
selects, it never writes.

## 1. Provision the local model (sysop, while the frontier is up)

    operators/petard/provision.sh [runtime_dir] [model_name]

petard cannot assume a model exists on the box, so setting one up is part of its job.
This provisions a small CPU sentence-transformer (reusing system torch, so the pull
stays small). It is used only to rank candidates, never to generate, so a weak model
is fine. This is contract C: sysop keeps petard ready while things work.

## 2. Extract capability cards from ground truth

    python3 operators/petard/cards.py <spec.json> --root <checkout> --out cards.json

A card pairs a command with its ground-truth purpose and its source. Cards are
generated, never authored: a shell script's header comment is the purpose and its
`Usage:` line is the command; a Makefile target's `##` comment is the purpose and
`make <target>` is the command; a universal infra command (`docker compose restart`,
`kubectl rollout restart`) is harvested from its own `--help`. There is no path to
hand-write a card, so it cannot drift from the tool it describes. See
`examples/eaf/petard-cards-spec.json` for a real source list.

## 3. Translate intent into a grounded command (when the frontier is down)

    "$runtime/venv/bin/python" operators/petard/translate.py cards.json "reset a password"

The local model embeds the query and the cards and picks the closest, using a hybrid
of semantic similarity (so "bounce" reaches "restart", "wipe" reaches "destroy") and
lexical overlap weighted toward the command signature (so a literal `[password]` in a
command beats a fuzzy match in prose). It returns the chosen card's command verbatim,
its confidence, and the runners-up, and below a confidence floor it says it has no
match rather than guess.

The command is always real ground truth. The worst the model can do is pick the wrong
real command, and it shows its confidence and alternatives so the operator can tell.
It can never invent a command that does not exist. That is the invariant.

## Raw retrieval, when cards are not enough

`build_corpus.py` is the lower level: it harvests raw lines from ground truth and does
ranked keyword retrieval with provenance. Use it to grep the operational surface when
a task has no card yet. A task that keeps coming up with no good card is the signal
for sysop to harvest a runbook entry for it (contract C again).

## Why this is the invariant

A petard that lies is worse than no petard. The concrete failure it prevents: a
hand-maintained flag table documented `--parent` for four months after the real flag
became `--parent-id`, and every operator who trusted it created orphans. petard's
answer is generated from the live command surface, and it points at a real command
rather than reciting a remembered one.
