# Foist plan: hoist's generalizations → skillc; the method is "grounding"

Design record, 2026-08-17. The plan for splitting what we built into its two real
layers, and moving the general parts to `skillc` where they belong. Plan-then-execute:
skillc is a mature, shipped project, so nothing moves until this is agreed.

## The two layers (settled, hoistable-985)

- **A = hoist** (stays in `hoistable`): ship and operate software. The operators
  (develop / preflight / sysop / petard), the deploy-and-operate discipline, the
  software-distribution product. A hoist skill is *a skillc skill whose task is
  deploy-and-operate*.
- **B = skillc** (already exists, shipped): the skill compiler and the self-building
  ouroboros. Build a self-building file; the receiver rebuilds it against *their* model
  and environment, tests on held-back examples, reports **built / honest-failure /
  cannot-build**. Same DNA as hoist (self-building file, receiver-rebuild, carry-vs-bind,
  the exact built/honest-failure/cannot-build vocabulary, a `seed/rebuild.skill.md`
  mirroring hoist's `seed/hoist-rebuild.md`).
- **The method = "grounding"**: a fresh agent does the real task on a real target; the
  honest transfer score is the loss; you descend it. Generalizes beyond skills to any
  multi-sided project with a real-target grade. This is skillc's named method.

Key fact about skillc: **it carries no build program** ("the engine is Claude itself, no
separate program and no service"). So the foist adds prose to skillc's seeds and docs, it
does NOT port hoist's `emit.py`. That matches both projects' doctrine: the skill is the
product; code is only a build convenience. hoist's `emit.py` cross-compile functions become
the *reference spec* for the prose skillc's builder follows, not code that moves.

## What skillc already has vs. lacks

Has: build (`seed/builder.skill.md`), receiver-side rebuild (`seed/rebuild.skill.md`),
honest-grade, held-back scoring, carry-vs-bind, proofs/attestations (`.attestations/`,
`*.proof.md`, Bitcoin-anchored).

Lacks exactly the three things hoist invented:

### Foist 1 — author-side cross-compile (target triple + delta overlay + provenance)
skillc adapts *on the receiver*; hoist added "measure where a weak receiver falls off and
pre-bake the correction, author-side, per target." Foist into skillc's builder prose:
- A **target triple** `(model, agent, environment)` a skill can be compiled for, declared
  by a `<!-- target: model=.. agent=.. reference=.. -->` line (from hoist's `_target_meta`).
- A **delta overlay**: shared core + a model-conditioned correction block, resolved at build
  time (hoist's `seed/deltas/<target>.md`). skillc gains a `seed/targets/` (or `deltas/`)
  library; `qwen-opencode` is the first target profile.
- The **neutral provenance header** (hoist's `_provenance_header`): every emitted skill
  self-declares its target, deltas, and earned grade (honest "not yet measured" default),
  with no vendor brand. skillc reconciles this with its existing proof/attestation line.
- Complementary, not a replacement: skillc's receiver-side rebuild stays; the delta is the
  author-side pre-tuning for a *known-weak* target.

### Foist 2 — grounding, the optimizer (descend a skill against a transfer-score loss)
skillc scores; it does not yet iterate-to-optimize. Foist the method (rename to grounding):
- Reference docs: hoist's `docs/design/skill-gradient-descent.md`,
  `skill-cross-compile.md`, `docs/design/corpus/METHOD.md` → skillc docs, in skillc's
  vocabulary, method named **grounding**.
- The loop: run a grounding episode (receiver does the real task on a real target) → grade
  honestly (transfer score = loss vs a reference) → localize where the weaker receiver
  diverged → edit the target delta → re-verify. With the anti-overfit / regression /
  convergence guards from METHOD.md (repeats, ≥2 targets, reference re-run, honest labeling).

### Foist 3 — grounding on reality (real-target grade, not just example pairs)
skillc grades on approved *example pairs*; hoist grades on a *running app on real infra*
(dind deploy, hard isolation). Generalize skillc's acceptance: a grounding test is
example-pairs OR a real-target task (deploy, hit an endpoint, operate a service). The
hard-isolation harness (receiver in its own sandbox, real target, honest transfer score,
the decision-B baseline) becomes skillc's grounding harness for real-world skills.

## What stays in hoistable (Layer A)

- `seed/hoist-rebuild.md` deploy discipline, the operators (develop/preflight/sysop/petard),
  `examples/<app>/` specs, the corpus evidence (`docs/design/corpus/`), the app marketplace
  scaffold, `/hoistable:build` + `/hoistable:run`. These are hoist's domain content, an
  *input* to skillc, not general machinery.

## The seams (how A consumes B after the foist)

- **Adopt-by-pin (decided 2026-08-17).** hoistable pins skillc at a specific version and
  adopts that pinned prose at *build time*. Not a live library import (coupling/break, the
  operate.py trap) and not a copy-fork (drift). skillc stays the single source of truth;
  hoist's build vendors/fetches skillc@`<pinned-sha>` with the content hash recorded, and a
  pin bump is a deliberate, re-validated act. This mirrors hoist's own pinning discipline (a
  hoist skill pins the code it fetches by URL + checksum). The emitted hoist skill remains
  self-contained: the pin is build-time, the receiver gets no skillc dependency. A small pin
  file in hoistable records skillc's sha + hashes; the reconcile step (below) points hoist's
  rebuild at the pinned skillc seed rather than a maintained copy.
- **Reconcile the two near-duplicate rebuild seeds.** `hoist-rebuild.md` and skillc's
  `rebuild.skill.md` are near-duplicates (both: rebuild against the receiver, the same
  built/honest-failure/cannot-build outcome, carry/bind). Make skillc's the ONE canonical
  rebuild; hoist's deploy discipline layers on top as a skillc skill's carried content.
  hoist stops maintaining its own rebuild seed.
- **hoist's `emit.py`**: likely retired (skillc is code-free); if it survives, only as
  hoistable's local build convenience, never shipped, never a surface skillc depends on.

## Migration sequence (outcomes)

1. skillc's builder seed gains cross-compile: target triple + delta overlay + provenance,
   as prose; a `seed/targets/qwen-opencode.md` profile. Verified: skillc emits a
   target-conditioned variant; canonical unchanged; provenance neutral.
2. skillc gains grounding: the optimizer loop + real-target grounding harness, as method
   docs + a grounding procedure. Verified: a grounding run on one skillc skill yields a
   transfer score, a delta edit, and a re-verify.
3. hoist becomes a skillc consumer: `/hoistable:build` compiles via skillc; hoist keeps the
   operators + deploy discipline; the duplicate compile/rebuild machinery is retired.
   Verified: `/hoistable:build` still produces a working self-hoisting skill, now via skillc.
4. Reconcile rebuild seeds (canonicalize skillc's) and unify provenance with skillc's
   proof/attestation line.
5. Adopt **grounding** across skillc + hoistable docs as the method's name.

## What NOT to do

- Do not rewrite skillc's shipped surface (marketplace, site, releases) — additive only.
- Do not extract past skillc (the rigging-repo lesson: extracted at one consumer, folded
  back).
- Do not import skillc as a library into hoistable's process.

## Decisions (resolved 2026-08-17, Baron)

1. **Seam = adopt-by-pin.** hoistable pins skillc and adopts the pinned prose at build time.
   Single source of truth = skillc; no drift, no live coupling. (See The seams, above.)
2. **skillc's rebuild seed becomes the ONE canonical rebuild**; hoist retires its
   near-duplicate `hoist-rebuild.md` and points at the pinned skillc seed. Confirmed.
3. **grounding = the method**; "cross-compile" stays for the author-side retarget step;
   "transfer score" stays as the loss metric. (Low-confidence naming call; revisit if it
   grates in use.)
