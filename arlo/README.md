# arlo

**A Real, Local Operator. Lights-out ops.**

When the frontier model is down and credits are out, you type your own words and arlo
hands back the exact command to run, grounded in your system's own ground truth. It
runs on an independent local path and **never invents a command** that isn't real.

arlo is agent-first: the interface is a skill an agent invokes, not a command line.
See [`SKILL.md`](SKILL.md) for how it is used. The Python here is the neutral core the
skill calls.

- `arlo/cards.py` — generate capability cards from ground truth (scripts, Makefiles, `--help`).
- `arlo/translate.py` — rung 0: select a card by intent, return its command verbatim.
- `arlo/binder.py` — rung 1: fill a real command template's slot from intent, skeleton never drifts.
- `arlo/build_corpus.py` — lower-level grounded retrieval over raw harvested lines.
- `provision.sh` — set up the frontier-independent local model (run while things work).

Depends on nothing but the standard library and a small local model (behind a lazy
import). Add it to any project by pointing a card spec at that project's real ground
truth. Design and lineage: [`../docs/arlo.md`](../docs/arlo.md).

Run the tests: `for t in tests/test_*.py; do python3 "$t"; done`
