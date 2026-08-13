---
name: petard
description: The no-frontier operational fallback. A fresh corpus of ground truth plus retrieval, run on an independent path, so the operator can still act when the frontier stack is down or rate limited. Never guesses.
---

petard keeps you able to operate when the frontier model is down or rate limited. It is
not autonomous ops and not a smart model. Its strength is a fresh corpus of ground truth
plus retrieval, on independent power and network. If it depends on the thing that is
down, it is not a petard.

## Build the corpus from ground truth

The corpus is generated, never authored. Build it by running commands and harvesting
what they say: `--help` dumps, live schema introspection, runbook harvests.

    python3 operators/petard/build_corpus.py build sources.json --out corpus.json

where `sources.json` is a list of `{name, cmd}`. There is no path to hand-write corpus
text, so it cannot drift the way a maintained doc does. sysop rebuilds it after any
change to the command surface (contract C).

## Answer by retrieval, never by memory

    python3 operators/petard/build_corpus.py ask corpus.json "<query>"

It returns the lines from the corpus that match, each tagged with the command that
produced them. It never synthesizes a command shape from memory. Every line it hands
back is present in the corpus. When there is no grounded match it says so; it does not
guess.

## Why this is the invariant

A petard that lies is worse than no petard. The concrete failure it prevents: a
hand-maintained flag table documented `--parent` for four months after the real flag
became `--parent-id`, and every operator who trusted it created orphans. petard hands
back the real flag from the fresh corpus instead.
