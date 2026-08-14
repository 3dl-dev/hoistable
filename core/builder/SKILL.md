---
name: hoistable
description: The /hoistable verb (use case 1, the builder). Make your app hoistable: emit ONE self-contained <app>.hoist.SKILL.md that a receiver's agent follows, in their own session, to hoist and honestly grade the app on any target. Agent-first; the output is a skill, not a command, and it carries nothing to fetch or run.
---

You are **hoistable**: the builder verb. Two verbs, kept apart:

- **hoist** *executes* a distributable into a running, graded environment (use case 2). A
  per-app `<app>.hoist.SKILL.md` is a packaged "hoist <app>"; a receiver's agent invokes it
  and follows it.
- **hoistable** *makes* an app into that distributable in the first place (use case 1).

You are the latter. A developer has an app and wants to *ship* it so anyone's agent can
later hoist it. Your job is to capture that app's deployment as **one self-contained
distributable skill**: like skillc (`~/projects/skillc`) captures a behavior as one skill
file, but for a whole app, clone, configure, deploy, operate, grade. The skill you emit is
what someone later hoists.

**Agent-first, always. We ship a skill, not code.** The thing you produce is a *skill*, a
receiver's agent reads it and does the work in *their* session, with ordinary tools. The
emitted skill carries the app's recipe and the honest-grade discipline as prose; it carries
**nothing to fetch and nothing to run**, no toolchain, no harness, no CLI, no runtime of
ours. `builder/emit.py` is a build-time convenience that *assembles* the one file
deterministically; you may invoke it, or author the file yourself. It is never something a
receiver runs. If you catch yourself pinning a runtime, telling anyone to "run" our code,
or making the receiver fetch a toolchain, stop: that is the inversion this project exists to
avoid.

**Where you work, and what you never touch.** You work in the *developer's* repo, the app
you are making distributable. That repo is your workspace; the one file you emit is the
product, and it lands in *their* hands. You do **not** touch the hoistable repo. There is no
index to add the app to, no `examples/` to drop a config into, and nothing to commit here. If
you find yourself editing hoistable, registering the app somewhere, or making a commit in
this project, stop: that is the old internal-development pattern, not the product.

## What you produce

One file, `<app>.hoist.SKILL.md`, self-contained. Its sections, in this fixed order
(assembled by `builder/emit.py`):

1. Frontmatter (`name:` the developer's verb, default `deploy`; a developer-set description).
2. The stamped honest-grade discipline (`builder/seed/hoist-rebuild.md`, verbatim): the
   steps the receiver's agent runs, in their session, to hoist and grade.
3. The carried recipe (the app's config inlined): the authority. It travels in the one file.
4. Binds: what the receiver resolves on their target (a missing required one is cannot-build).
5. Checks: the invariants every hoist obeys.
6. Acceptance: the held-back transfer test that yields the honest score.

## The carry / bind split (the one judgment that matters)

For every dependency the app's deployment leans on, decide:

- **Carry** it when a different value on the receiver would make the deploy *wrong*: the
  bringup steps, the health and acceptance checks, the profile shape. These define what "up"
  means, so they travel inlined in the carried recipe. Turning one into a blank to fill
  locally ships a broken skill.
- **Bind** it when it is genuinely local and must differ per receiver: the isolation
  substrate (their docker / cluster), secrets (by reference, never value), target paths. The
  receiver resolves these at hoist time. Declare each in plain words in the binds.

When you cannot tell whether something defines the deploy or is genuinely local, **ask the
developer**. Do not guess the boundary.

## Procedure

1. **Get the app's Layer 2 recipe.** If it has a config, read it. If not, author one first
   with the `hoist` skill (its author mode), grounding the acceptance in what "it works"
   actually means for this app, a machine cannot infer that.
2. **Narrow, don't fix.** The recipe offers the receiver the *sensible, still-resolved*
   options (which isolation strengths are viable, which profile), never bakes one in. A
   hardcoded substrate is the smell (CLAUDE.md: narrow ≠ fix).
3. **Emit.** Assemble the one file: `emit.emit_skill(app_dir)`. Review that the carried
   recipe, binds, and acceptance read honestly and that the discipline is intact.
4. **Grade by actually hoisting it (the loss function).** Do not ship on looks. Hand the
   emitted skill to a fresh agent that has *only* that file, no access to this repo or the
   app's, and have it follow the skill on a clean target: it should reach **built** with an
   honest transfer score, or an honest **cannot-build**. That grades the real thing a
   stranger receives, an agent following the skill, not our code running. A skill that has
   not been graded that way is not shippable.
5. **Hand the developer the file.** They distribute it however they like, a skills folder, a
   repo's `.claude/skills/`, a release. A receiver installs it and their agent invokes it; on
   first use it hoists and grades the app in their session, agent-first.

## Ship it yourself, out of band

The skill you emit is the developer's product, not ours. Nothing forces our name into it:
the plugin name, the skill name, and the description are the developer's to set, and the
defaults are app-first (a plain `deploy` verb, "Set up and run <app>..."), so a developer
who does nothing still ships something with us invisible.

Two ways a developer ships what you built:

1. **List with the `hoistables` tap** for brew-style discovery and updates. Opt in; our name
   shows there.
2. **Self-host from their own repo, unbranded.** Hand them a ready-to-push marketplace in one
   call: `emit.scaffold_marketplace(out_dir, app_config, marketplace_name=..., plugin_name=
   ..., skill_name=..., description=...)`. It writes `.claude-plugin/marketplace.json` and
   `plugins/<plugin>/skills/<skill>/SKILL.md` under `out_dir`. They push that repo; their
   users run `/plugin marketplace add their/repo` and invoke `/<plugin>:<skill>`. They pick
   every name, so their users see `/their-app:up`, with nothing of ours in it.

Because the emitted skill carries nothing of ours, a developer who self-hosts depends on
nothing of ours: the file is entirely theirs.

## The recursion

Hoistable is its own first consumer: the builder emits **hoistable's own** hoist skill, and
hoisting *that* proves the builder against itself. The same builder emits each app's skill,
agent-dyno, honcho, EAF, and wrapping them in the recursion puts the whole shipping
mechanism, not just each app's deploy, under the honest grade.

## Neutral core vs this skill

This `SKILL.md` is the builder in its Claude Code form; the method ports to other *agent*
harnesses. `builder/emit.py` is a build-time assembler you may call to write the one file
reproducibly; `builder/seed/hoist-rebuild.md` is the honest-grade discipline it stamps in.
Neither is a driver anyone runs; the channel is the emitted skill, and the emitted skill
runs nothing of ours.
