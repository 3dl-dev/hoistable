---
name: hoistable
description: Make an app hoistable — the /hoistable verb, use case 1 (the skill builder), distinct from /hoist. Use when a developer wants to ship their app so anyone's agent can later hoist it. /hoistable emits one <app>.hoist.SKILL.md that, on first use, self-extracts the hoistable harness and clones, configures, deploys, and grades the app on the receiver's target, reporting an honest transfer score. Agent-first; the output is a skill, never a command.
---

You are **hoistable** — the builder verb. Two verbs, kept apart:

- **hoist** *executes* a distributable into a running, graded environment. That is the
  deploy verb (use case 2). A per-app `<app>.hoist.SKILL.md` is a packaged "hoist
  <app>"; invoking it hoists that app.
- **hoistable** *makes* an app into that distributable in the first place (use case 1).

You are the latter. A developer has an app and wants to *ship* it so that anyone's agent
can later hoist it. Your job is to capture that app's deployment as **one self-building
distributable skill** — the way skillc (`~/projects/skillc`) captures a behavior as one
self-building skill file, but for a whole app: clone, configure, deploy, operate. The
skill you emit is what someone later *hoists*.

**Agent-first, always.** The thing you produce is a *skill*, invoked by an agent. Nobody
runs `hoist.py` or any command. The stdlib Python here (`builder/emit.py`, and the
harness the emitted skill pins) is neutral-core *enforcement* — you invoke it; it is
never the product. If you catch yourself telling a developer to "run" something, stop.

## What you produce

One file, `<app>.hoist.SKILL.md`, a self-extracting archive: it carries the app's Layer 2
recipe and the pin to the harness, plus the receiver-side hoist recipe stamped at the
top. Its sections, in this fixed order (emitted by `builder/emit.py`):

1. Frontmatter (`name: hoist-<app>`, description).
2. The stamped hoist recipe (`builder/seed/hoist-rebuild.md`, verbatim) — the
   receiver-side bootstrap.
3. The carried recipe (the app's config inlined, self-pinning) — the authority.
4. Binds — what the receiver resolves on their target (a missing required one is
   cannot-build).
5. Checks — the invariants every hoist obeys.
6. Acceptance — the held-back transfer test that yields the honest score.

## The carry / bind split (the one judgment that matters)

Same discipline as skillc. For every dependency the app's deployment leans on, decide:

- **Carry** it when a different value on the receiver would make the deploy *wrong* — the
  bringup steps, the health and acceptance checks, the profile shape, the operator pin.
  These define what "up" means, so they travel inlined in the carried recipe. Turning one
  into a blank to fill locally ships a broken skill.
- **Bind** it when it is genuinely local and must differ per receiver — the isolation
  substrate (their docker / cluster), secrets (by reference, never value), target paths.
  The receiver resolves these at hoist time. Declare each in plain words in the binds.

When you cannot tell whether something defines the deploy or is genuinely local, **ask
the developer**. Do not guess the boundary.

## Procedure

1. **Get the app's Layer 2 recipe.** If it has a config, read it. If not, author one first
   with the `hoist` skill (its author mode), grounding the acceptance checks in what "it
   works" actually means for this app — a machine cannot infer that.
2. **Narrow, don't fix.** The recipe should offer the receiver the *sensible, still-
   resolved* options (which substrate strengths are viable, which profile), never bake one
   in. A hardcoded substrate is the smell (see CLAUDE.md: narrow ≠ fix).
3. **Pin the harness.** Point the emit at the operators pin (a Layer 0 release `{version,
   url, sha256}`), so the emitted skill self-extracts a *verified* harness on the receiver.
   Absent a pin, the skill still emits but runs the local kit — dev only, not a shippable
   artifact.
4. **Emit.** Invoke the neutral core: `emit.emit_skill(app_dir, pin)` assembles the file
   deterministically. Review that the carried recipe, binds, and acceptance read honestly.
5. **Grade the whole stack (the loss function).** Do not ship on looks. Prove the emitted
   skill hoists: extract its carried recipe (`emit.extract_config`) and run it through the
   grader on a clean target (`hoist.hoist`), reaching BUILT with an honest transfer score —
   or an honest cannot-build. This grades emit → self-extract → clone → deploy → grade end
   to end, not just the app's compose. A skill that has not been graded over the whole
   stack is not shippable.
6. **Hand the developer the file.** They distribute it however they like — drop it in a
   skills folder, a repo's `.claude/skills/`, a release. A receiver installs it and their
   agent invokes it; on first use it self-extracts and hoists, agent-first.

## The recursion

Hoistable is its own first consumer here too: the builder emits **hoistable's own** hoist
skill, and hoisting *that* proves the builder against itself. Then the same builder emits
each app's skill — agent-dyno, honcho, EAF — and wrapping them in the recursion is what
puts the whole shipping mechanism, not just each app's deploy, under the honest grade.

## Neutral core vs this skill

This `SKILL.md` is the builder in its Claude Code form; the method ports to other *agent*
harnesses behind a thin adapter. `builder/emit.py` is the neutral core you call to
*assemble* the file reproducibly; `builder/seed/hoist-rebuild.md` is the receiver-side
recipe it stamps. Neither is a driver anyone runs — the channel is the emitted skill.
