# Skill cross-compilation

Design record, named 2026-08-15 from the qwen/opencode work. Forward direction, not a
frozen conclusion. The live parts (any transfer score, the current target variant) are
re-derived per episode, never remembered here.

## The move

Take a skill that is authored and graded on a **reference substrate** (a strong model on
a capable agent) and retarget it so it runs with the same *graded* quality on a
**different, usually weaker substrate**. The mechanism is the descent loop in
`skill-gradient-descent.md`. The concept is a **cross-compile**: hoist is a cross-compiler
for skills.

## The analogy, made exact

| Compiler | Skill cross-compile |
|---|---|
| Source program | the skill's prose (carried recipe + honest-grade discipline), authored on the reference substrate |
| Target triple (arch-vendor-os) | the receiver: **(model, agent-harness, environment)**, e.g. `(Qwen3.8-27B-Q8, OpenCode, <env the operator resolves>)` |
| Native build | the skill run by the author substrate (Claude/Sonnet); its honest transfer score is the native behavior to match |
| Compiler | opus 4.8 running the descent loop; it retargets the prose to what the target actually offers |
| Codegen / object code | the emitted model-conditioned variant = shared core + a **target delta overlay** (the `emit.py --receiver` mechanism, built in hoistable-c7c) |
| Optimization passes | prose edits that fix where the weaker receiver falls off the recipe, retargeted per triple |
| Correctness / test suite | the ouroboros honest transfer score on a **real** target: the cross-compile is correct iff the target build passes the *same* acceptance the native build passes |
| Loss | the parity gap: `score(reference) - score(target)` on the same deploy |

## Why this is the special thing

- A skill authored once on a frontier model can be retargeted to cheaper / local /
  other-vendor agents, and the transfer score **proves** the retarget worked. Not hope: a
  graded correctness check you cannot fake, because it runs in the receiver's own session
  on a real target.
- Honest by construction. A cross-compiled binary that segfaults on the target fails its
  tests; a cross-compiled skill the weaker model cannot follow scores low. You cannot ship
  an unearned retarget, the same way you cannot ship a binary that fails the target suite.
- The target is **resolved, not fixed** (anti-constrain). The triple is a parameter, not a
  menu. `(Qwen3.8-27B-Q8, OpenCode, dind)` is target #1, never the only target.

## Targets span platforms, local or hosted

The receiver triple's model and environment are not restricted to a local GPU. A target
can be a hosted API model on someone else's platform just as well as a self-hosted GGUF.
The environment axis ranges over "wherever the receiver agent runs and whatever it deploys
into." Candidate targets:

- `(Qwen3.8-27B-Q8, OpenCode, <resolved env>)` - self-hosted model, target #1 (in flight,
  hoistable-9a5). dind was only what *this host* resolved the environment axis to for the
  baseline; the axis is whatever the operator wants and the receiver offers.
- `(DeepSeek-V4-Flash, <agent>, <resolved env>)` - a hosted platform model, target #2.
- any `(model, agent, environment)` a receiver can present.

**The environment axis is resolved, not fixed** (anti-constrain, principle 3). honcho's
`require: environmental` means "resolve the strongest environmental isolation the target
actually offers" - a cloud, a k8s namespace, a VM, a throwaway container, whatever the
operator wants - not "use dind." We cross-compile to what the operator wants; we never
optimize the skill *for* a sandbox we happened to pick. Fixing the environment to dind
would be exactly the narrow-becomes-fix failure the doctrine warns against.

This is the payoff: author a skill once on a frontier model, then cross-compile and
*prove* it onto the whole matrix of platforms - local and hosted, across vendors, into
whatever environment the operator resolves - each build labeled with the parity it actually
earned. The compiler and the correctness test do not change with the target; only the delta
overlay does.

## What it is NOT

- Not fine-tuning the model. The model is fixed; we retarget the **prose**.
- Not optimizing the app's install. Honcho's carried recipe stays fixed across episodes,
  or the experiment is confounded. We retarget the *hoist discipline*, not the app.
- Not software that "does" the compile. The compiler is an **agent running a loop**
  (build-rule 1). No runtime of ours.
- Not a fork per target. Shared core + a target delta overlay, resolved at emit time
  (narrow != fix). A delta that generalizes to a second app promotes back to the core.

## The general skill (hoistable-e14)

`cross-compile a skill to a target triple`.

- **Inputs**: source skill, reference substrate, target triple, a real acceptance graded
  on a real target.
- **Loop**: emit target variant -> run one episode on the target (the receiver follows the
  skill in its own session) -> grade honestly -> localize the first divergence -> edit the
  target delta -> repeat until parity or a stop criterion.
- **Output**: a target-conditioned variant plus its **earned** transfer score, labeled with
  exactly the parity it reached, never the one we wanted.

## Provenance / status

Concept named 2026-08-15 from the qwen/opencode work. Mechanism designed in
`skill-gradient-descent.md`. Native baseline recorded in `honcho-baseline-sonnet.md`
(score_sonnet = 3/3). First target build `(Qwen3.8-27B-Q8, OpenCode, dind)` in flight
(hoistable-9a5); its score is re-derived per episode, never frozen into this file.
