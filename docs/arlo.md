# arlo: a real, local operator (extracting petard as a standalone product)

**arlo** is petard pulled out of hoist to stand on its own, so a user can add it to
**any** repo, independent of hoist, and so hoistable can package it the same way it
packages any app. Tracked as `hoistable-12c`.

The name matters: "petard" only ever worked *inside* hoist (the "hoist by your own
petard" pun) and reads badly on its own. The standalone product is **arlo, A Real,
Local Operator**, lights-out ops. "Real" is the invariant: it hands you a real
command, never an invented one. hoist keeps its operator named **petard** (the pun
stays home); hoist's petard operator becomes "hoist consuming the arlo skill."

## What arlo is

The no-frontier operational fallback: when the frontier model is down and credits are
out (the lights are out), you type your own words ("bounce the deriver", "reset a
password") and arlo hands back the exact command to run, grounded in the system's own
ground truth. It runs on an independent path (local model, no frontier network).

The invariant is narrow and sacred:

> **arlo never invents a command that is not real ground truth.** The worst it can do
> is surface the wrong *real* command, and it shows its confidence and the
> alternatives so the operator can tell.

The failure it exists to prevent: a hand-maintained flag table documented `--parent`
for four months after the real flag became `--parent-id`, and everyone who trusted it
created orphans. arlo answers from the live command surface.

## Why the extraction is cheap (the seams already existed)

- The core (`cards.py`, `translate.py`, `build_corpus.py`) is **stdlib only**, zero
  hoist imports.
- Dependency direction was already correct: hoist's `sysop` called *into* petard;
  petard called nothing of hoist's.
- The one coupling, "run a command in this environment", was already
  dependency-injected. The host runner (`_host_run`) runs on the host; an injected
  `environment_runner` runs wherever the system actually lives. arlo names nothing
  about your environment; you inject how to reach it.
- The embedder is pluggable (`rank(embed, ...)`), so grounding is testable with a
  deterministic model-free embedder.

So the real extraction is a **move**, not a rewrite, and hoist reacquires arlo through
its own emit/package mechanism (it packages arlo, then consumes the skill it built):
no drift, no new dependency type. Reserved to Baron and gated on `hoistable-12c`:
vendor-with-pin vs reference, and when to cut the actual repo.

## The design center: a grounded LOM on a labeled trust gradient

petard's original rule, *"the model selects, it never writes,"* collapsed two things:
the real invariant (**never invent a command that isn't ground truth**, sacred) and a
weak implementation of it (**only cosine-rank a fixed card list**, which leaves most
of a capable local model on the table). arlo keeps the first and drops the second: the
local model (the **LOM**) does the hardest thing it can while still pointing at ground
truth, and every answer is **labeled with the trust it earned**.

| Rung | Capability | Grounding | Status |
|---|---|---|---|
| 0 | rank-and-return a card verbatim | full | **built + tested** |
| 1 | **slot-fill a real card template** (bind args into a verbatim skeleton) | skeleton real, slot inferred | **built + tested** |
| 2 | reason-rank / disambiguate with an explainable *why* | full | designed |
| 3 | explain / dry-run narrate the chosen real command | full | designed |
| 4 | compose real cards | per-atom real, composition inferred | designed |
| 5 | synthesize a card from source it reads (human reviews) | summarizes real source | designed |
| 6 | free NL→shell generation for the genuine no-card tail | none, labeled unverified | designed |

Rungs 0–3 keep the invariant fully intact. Rung 1 is the first step past lookup and
the design center: cards are real command *templates* (`docker compose restart
[service]`), and the LOM binds the argument from intent ("bounce the deriver" →
`docker compose restart deriver`). Structurally, a binder only ever returns slot
*values*; `fill()` assembles the command from the real template, so no binder,
deterministic or a large model, can alter the skeleton. A slot value carrying shell
metacharacters is refused so a hole cannot chain a second command.

## The generative parallel, reviewed and placed

`ThorOdinson246/whatisit-nl2sh` (Qwen2.5-Coder-1.5B, GGUF Q4_K_M, 941MB, ~1.6GB
resident, ~0.6s CPU, 62% InterCode-ALFA) proves a capable NL→shell model runs locally
in ~1s. It is also arlo's **inverse**: free generation, "emits commands that will
destroy data," ~11% adversarial corruption, safety a denylist "not a sandbox." So it
is **not** a drop-in engine, that breaks the invariant; its only place is rung 6,
labeled ungrounded. Two things are worth harvesting regardless:

- **Its DANGER/CAUTION denylist.** arlo has no safety layer today because ground truth
  *was* its safety. The moment a generative rung (or any model-controlled slot value)
  exists, that guarantee weakens, so a denylist over the assembled command is needed.
  The metacharacter guard in `binder.py` is the minimum floor; the full denylist is
  the later layer.
- **InterCode-ALFA as an honest yardstick.** arlo has no NL→command accuracy
  benchmark; even the grounded rungs deserve one.

The point is not the NL2SH product: it is that **more local capability is leverageable
than a simple lookup**. The trust gradient is how arlo takes that capability without
paying for it in honesty.

## Runtime cost, stated honestly

Rungs 1–5 want a small instruct/coder LOM (a gguf served by `llama.cpp`), a
**different model class** than today's rank-only sentence-transformer embedder.
`provision.sh` resolves the embedder now (rung 0); the gguf lands with those rungs.
whatisit's envelope (~1GB disk, ~1.6GB resident, sub-second CPU) is the ballpark:
affordable for a fallback that only runs when the frontier is down.

## What the spike proved (`arlo/`), and what it did not

Proved, for real and hermetically (deterministic embedder/binder, no model download,
exactly as arlo's existing grounding test works):

1. **Clean carve** — `arlo/` imports nothing hoist-specific; `grep` for
   petard/substrate/contract/sysop/envelope in the code is clean; its tests run on
   their own.
2. **Host-run path** — arlo harvests a card from real ground truth on the box (a
   script's `Usage:` line and `ls --help` via `_host_run`) and translates a query into
   that card's command verbatim. No substrate, no frontier, no injected environment.
3. **Rung 1** — the binder fills a real template's hole from intent, and
   `skeleton_intact` proves the fixed scaffolding never drifts; a binder that returns
   a whole command changes nothing, and a slot value smuggling `; rm -rf /` is refused.

12 tests pass (`tests/test_grounding.py`, `tests/test_host_translate.py`).

Not done, stated plainly:

- No live LOM provisioned or graded. The *quality* of a real model's ranking or
  slot-binding needs a provisioned gguf; the spike grades the grounding **mechanics**
  and labels live-model inference as the boundary.
- Rungs 2–6 not built; the full DANGER/CAUTION denylist not built (only the
  metacharacter floor).
- No repo cut, vendor pin, or reference wiring, reserved to Baron on `hoistable-12c`.
