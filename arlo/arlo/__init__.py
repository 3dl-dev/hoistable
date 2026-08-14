"""arlo: the no-frontier operational fallback.

You type your own words when the frontier model is down and credits are out, and
arlo hands back the exact command to run, grounded in the system's own ground
truth. The invariant is narrow and sacred: arlo never invents a command that is
not real ground truth. The worst it can do is surface the wrong real command, and
it shows its confidence and the alternatives so the operator can tell.

Standalone project. Depends on nothing but the standard library (the production
local model lives behind a lazy import, so the package stays importable and
testable with no model installed). Submodules: build_corpus, cards, translate,
binder. Import the one you need (`from arlo import binder`); they are not eagerly
imported here so each also runs cleanly as `python3 -m arlo.<name>`.
"""

