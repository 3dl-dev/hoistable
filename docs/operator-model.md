# Operators as meta-skills; build-time as narrowing; how Hoistable is distributed

Design direction captured 2026-08-13. This is forward direction (the model, the
invariants, the open decisions), not a frozen conclusion. Re-derive the live parts
every run.

Hoistable exists to solve the **app-distribution knowledge-and-experience cliff**: the
vast gap of expertise and per-environment judgment a developer or user must cross to
take software from a repo to a running, operated system. Everything below is how it
crosses that cliff.

It crosses that cliff **agent-first**: the distribution channel is *skills*, invoked by
agents, nobody reaches for a command line. `hoist` is a skill; every product Hoistable
wraps becomes its own distributable skill; and the stdlib Python (`hoist.py`,
`envelope.py`) is neutral-core *enforcement* behind the skill, never the product surface.

## Operators are meta-skills that compose expertise

Each operator, develop, preflight, sysop, petard, is **not** a from-scratch reasoner
and **not** a fixed program. It is a **meta-skill**: it pulls in and composes skills and
best practices, some we author, many consumed from the public sphere, to be an expert
in its domain.

- **develop**: development expert (how this kind of software is built, tested,
  forked, contributed).
- **preflight**: deployment-planning expert (scopes the deploy with the user; narrows
  the option space against the target's manifest and the operator's policy).
- **sysop**: operations expert. Already the model: sysop *composes external skills*
  (AWS/Azure/SSL/SSO/monitoring) and does **not** embed infra knowledge.
- **petard**: backup-operator expert (frontier-independent continuity: operate and
  recover even with the cloud or the frontier down).

The expertise is **resolved in**, the same verb everything else in Hoistable resolves
by. A missing skill is a resolved slot, authored just-in-time or pulled from the public
sphere when an operator's problem needs it, then cached as a recipe. It is never a
hardcoded menu of "the skills we support."

## Build-time is narrowing the universe, not solving it

A naive agent and a naive user, dropped in front of "deploy this app," face a **huge
universe** of options: every substrate, every deploy topology, every secret backend,
every scaling and operations and backup choice. Swimming through that universe *is* the
cliff.

Making a product hoistable, the develop/build-time act, is the **expert collapse of
that universe** to a small, sane, still-resolved-and-overridable set. Nudge, not lane.

**NARROW ≠ FIX.** Narrowing *reduces the search space* the naive party swims through
while keeping the choice **resolved at the user's runtime** and **overridable**. Fixing
bakes one option in and *deletes* the user's choice. (Recorded failure, 2026-08-13:
hardcoding an app's substrate into its shipped config, `honcho depends_on docker-host`.
That deleted the option space instead of narrowing it, and deleted the user's runtime
choice with it. Backed out.)

## How Hoistable is distributed (current model)

Two plugin marketplaces, agent-first (see `docs/marketplace.md` and the README for the commands).

- **The tools** live in `3dl-dev/hoistable` as one plugin, `hoistable`, with two skills: `/hoistable:build` (make your app a self-installing skill) and `/hoistable:run` (run a recipe). This is the only place our name shows.
- **A built app** is one self-contained `SKILL.md`. It carries the app's recipe inlined and a pin to the harness, and on first use a receiver agent self-extracts the harness, deploys, and grades. The developer chooses the plugin name, the skill verb, and the wording; the defaults carry none of our naming.
- **A developer ships it from their own repo** (a one-plugin marketplace the build step scaffolds), or lists it in the shared tap `3dl-dev/hoistables`. Either way, `build` touches nothing of ours: no index, no `examples/` here, no commit to this repo. The output is one file in the developer's hands.

The operators (develop, preflight, sysop, petard) travel inside the built skill so the user can operate what they deployed, not merely install it.

There is no index and no by-name discovery in the product; those were an earlier brew-style idea, replaced by plugin marketplaces. (`hoist.py` still has a dormant by-name branch as neutral-core plumbing; it is not how anyone uses this.)
