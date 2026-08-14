---
name: arlo
description: "Lights-out ops. A real, local operator: when the frontier model is down and credits are out, you type your own words and arlo hands back the exact command to run, grounded in your system's own ground truth. It never invents a command."
---

# arlo, a real, local operator

arlo keeps you able to operate when the lights go out, when the frontier model is
down or rate limited and you still need to act. You type your own words ("bounce the
deriver", "reset a password", "restart"), and arlo hands back the command to run. It
runs on an independent path (local model, no network to the frontier). A pile of docs
nobody reads at 3am is not arlo; a model that makes up plausible commands is worse.

**The invariant is narrow and sacred: arlo never invents a command that is not real
ground truth.** The worst it can do is surface the wrong *real* command, and it shows
its confidence and the alternatives so you can tell. It can never hand you a command
that does not exist. The concrete failure this prevents: a hand-maintained flag table
documented `--parent` for four months after the real flag became `--parent-id`, and
everyone who trusted it created orphans. arlo answers from the live command surface.

## The trust gradient

arlo's honesty is not "it only does lookup." It is that every answer is **labeled
with the trust it earned**. The local model's job rises as far as it can while still
pointing at ground truth:

- **rung 0, retrieval** *(built)*: select a capability card and hand back its command
  verbatim. Full grounding.
- **rung 1, slot-fill** *(built)*: bind the argument of a real command *template*
  from your words ("bounce the deriver" -> `docker compose restart deriver`). The
  command skeleton is still verbatim ground truth; only the slot value is inferred,
  and it is shown so you see exactly what was bound.
- **rungs 2-3, reason-rank / explain** *(designed)*: pick with an explainable *why*;
  narrate what the chosen real command will do. Still grounded.
- **rungs 4-6, compose / propose / generate** *(designed)*: chain real cards, propose
  a card from source, and only at the very end free generation for the genuine
  no-card tail, each labeled less-trusted, generation labeled *unverified*.

## 1. Provision the local model (while the frontier is up)

    arlo/provision.sh [runtime_dir] [model_name]

arlo cannot assume a model exists on the box, so setting one up is part of its job.
It provisions a small CPU model on an independent path. Do it while things work, so
arlo can answer when they do not.

## 2. Extract capability cards from ground truth

    python3 -m arlo.cards <spec.json> --root <checkout> --out cards.json

A card pairs a command with its ground-truth purpose and its source. Cards are
generated, never authored: a shell script's header comment is the purpose and its
`Usage:` line is the command; a Makefile target's `##` comment is the purpose and
`make <target>` is the command; a universal infra command (`docker compose restart`,
`kubectl rollout restart`) is harvested from its own `--help`. There is no path to
hand-write a card, so it cannot drift from the tool it describes.

## 3. Translate intent into a grounded command (when the lights are out)

    "$runtime/venv/bin/python" -m arlo.translate cards.json "reset a password"

The local model embeds the query and the cards and picks the closest, hybrid of
semantic similarity (so "bounce" reaches "restart") and lexical overlap weighted
toward the command signature. It returns the chosen card's command verbatim, its
confidence, and the runners-up, and below a confidence floor it says it has no match
rather than guess.

## 4. Fill the blank in a real command (rung 1)

    python3 -m arlo.binder card.json "bounce the deriver"

When the chosen command is a template with a hole, arlo binds the hole from your
words. It returns slot *values* only; the command is assembled from the real
template, so the skeleton can never drift. Unbound slots are shown as blanks for you
to fill. Off the box a local model does the binding; a deterministic binder ships so
the mechanism runs and is tested with no model installed.

## Adding arlo to any project

arlo depends on nothing but the standard library and a small local model. Point its
card spec at your project's real ground truth (scripts, Makefiles, the `--help` of
the infra commands you actually run), provision the model once, and arlo answers from
that surface. It names nothing about your environment; if your system runs somewhere
other than the host, inject how to reach it (`build_corpus.environment_runner`) and
arlo harvests from there instead.

## Why this is the invariant

An arlo that lies is worse than no arlo. Its answers are generated from the live
command surface and point at a real command rather than reciting a remembered one.
The model *selects and fills*; it never *writes* the command shape. That is the line
that keeps every rung honest.
