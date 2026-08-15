---
name: optimize-loop
description: "The outer loop, as a skill. Take a bundle (a skill/product), run it in-situ, score the run on what actually decides success, back-propagate the loss to the bundle as generalizable patches, and climb — avoiding the known traps that otherwise get re-derived through painful operator correction. It too is a bundle: score and iterate it."
---

# Optimize a bundle: run it, score its run, iterate

> **Ownership: this is a hoistable builder-layer skill — the outer loop, generic over any
> bundle (a skill/product). It lives here, in hoistable's toolkit. Consumers (arlo, and any
> other repo) reuse it by *invoking* it, they do not own it or fork a private copy; derived
> in arlo, promoted here. The self-referential "it too is a bundle" note at the bottom is the
> hoistable-optimizes-itself recursion; acknowledge it, don't spin on it.**

This is the **outer loop** — the meta-skill that improves another skill (the *bundle*). The
bundle is run in-situ, its run is scored against what actually matters, the loss is attributed
to the bundle, and the bundle is patched. Repeat, climbing until the score plateaus at the
ground-truth or operator ceiling. (In hoistable this loop drives the ouroboros grader in
`grade/`: `grade/GRADE.md` is the loss function, an agent following an emitted skill on a
real target. A consumer plugs in its own agent-driven grader the same way.)

The loop is simple. The **traps** below are the whole value of this document: each one was
paid for by an operator correcting an agent that walked straight into it. Read them before you
run the loop, not after.

## The loop

1. **Collect held-out cases** the bundle must handle — real, drawn from real targets, *hard*
   (they exercise the capability, not the happy path).
2. **Run the bundle in-situ**, agent-driven: an agent follows the bundle on a real target and
   produces real output. Not a hand-built instance, not a description of what it would do.
3. **Score the run** with adversarial judges, on the metric that *decides success* — and
   re-verify the judges' checks yourself; do not trust self-reports.
4. **Synthesize the loss**, decomposed by failure type, each attributed to a specific bundle
   deficiency.
5. **Patch the bundle** — natural-language, generalizable — for the dominant failure only.
6. **Re-run and compare.** Loss falls → keep it; flat or worse → the diagnosis was wrong,
   re-diagnose. Climb.

## The traps (do not re-derive these)

- **Run the loop; don't ship a one-shot demo or "a quick script."** The loss is the bundle
  *executed in situ and graded*, not a thing you hand-built to look like success. The instant
  you catch yourself producing the artifact instead of running the bundle that produces it, stop.
- **Only real, never fabricated — and verify, don't trust.** Do not hand-author the output you
  are about to score; run the bundle and capture verbatim. When an agent reports its own scores
  or grounding booleans, **re-run the check yourself** — a fabricated absence-check ("grep finds
  nothing") is the invariant broken on the honesty axis. If it isn't real, it isn't a datapoint.
- **No thumb on the scale.** Do not leak the answer into the prompt — not the tool's name, not
  the steps, not the target's identity. Naming the thing the bundle is supposed to *discover* is
  the tell. And **control for the confound that the agents already know your shared tools**: a
  subagent that recognizes `rd`/git/docker didn't *discover* it. De-leak the bundle of tool
  names, test on cases the target doesn't declare, and force an honest self-report of whether
  the answer came from evidence or recall.
- **Score the thing that decides success, not the easy proxy.** "Recite a pre-written checklist"
  is not "infer a process." "Grounded" is not "correct" — a command can be verbatim-real and
  still not the source that *governs* the outcome. Pick the metric that says whether the output
  would actually work, and make the judges adversarial about it (penalize the proxy hard).
- **Improve the bundle; do not build apparatus.** The loss back-propagates to *natural-language
  bundle patches that generalize* — a principle, not the answer to case N. If you are writing
  code to grade, to harness, to do the task, or a data-shape to hold "all cases," stop: that is
  the apparatus this loop exists to avoid. Prefer the smallest skill line that removes a failure
  *class*.
- **Inner loop vs outer loop — put behavior in the right ring.** A behavior that should happen on
  *every run* belongs INSIDE the bundle (inner loop); the outer loop only measures and patches.
  If you find yourself orchestrating in the outer ring what the bundle should do in-situ (e.g.
  distilling its own outputs, self-checking, capturing), move it into the bundle. The outer loop
  is *small*; most compute should go to the bundle being *used*.
- **Single-sample is noise; read trends, not the aggregate.** A stable case can crater on one
  flaked sample and swamp a round of real improvement. Multi-sample (median, drop flakes) to
  measure a climb; and always read the *per-case* trajectory — a rising per-case trend under a
  jittery mean is real progress the aggregate hides.
- **Pin the set for A/B; rotate it for generalization.** Same held-out cases across a patch
  isolate the skill change; fresh cases test whether the patch generalizes or you are overfitting
  the prompt to the test set. Do both, deliberately.
- **Each round's regressions are usually the NEXT failure layer, not noise.** A patch that fixes
  the dominant failure often exposes the one beneath it (fix "wrong source" and "wrong *branch* of
  the source" surfaces). Read the synthesis, attribute, patch, re-run — that is the climb, not a
  setback.
- **Name the compute honestly.** This loop's cost is model-inference tokens (agents reading and
  reasoning), not CPU/GPU — and it is a *dev/optimization* cost, separate from what *using* the
  bundle costs. Say which you're spending, and don't spend a large multiple on your own say-so:
  climbing to a ceiling via multi-sample rounds is a real commitment — surface it as a decision.

## It too is a bundle

This skill is optimized the same way: run it (an agent uses it to improve some bundle), score
its run (did following it produce a *real* loss drop without tripping a trap above?), and patch
*this* file for the trap it failed to prevent. hoistable is meta's meta; so is its optimizer.
