# Operators as meta-skills; build-time as narrowing; the three ways Hoistable is used

Design direction captured 2026-08-13. This is forward direction (the model, the
invariants, the open decisions), not a frozen conclusion. Re-derive the live parts
every run.

Hoistable exists to solve the **app-distribution knowledge-and-experience cliff**: the
vast gap of expertise and per-environment judgment a developer or user must cross to
take software from a repo to a running, operated system. Everything below is how it
crosses that cliff.

It crosses that cliff **agent-first**: the distribution channel is *skills*, invoked by
agents — nobody reaches for a command line. `hoist` is a skill; every product Hoistable
wraps becomes its own distributable skill; and the stdlib Python (`hoist.py`,
`envelope.py`) is neutral-core *enforcement* behind the skill, never the product surface.

## Operators are meta-skills that compose expertise

Each operator — develop, preflight, sysop, petard — is **not** a from-scratch reasoner
and **not** a fixed program. It is a **meta-skill**: it pulls in and composes skills and
best practices — some we author, many consumed from the public sphere — to be an expert
in its domain.

- **develop** — development expert (how this kind of software is built, tested,
  forked, contributed).
- **preflight** — deployment-planning expert (scopes the deploy with the user; narrows
  the option space against the target's manifest and the operator's policy).
- **sysop** — operations expert. Already the model: sysop *composes external skills*
  (AWS/Azure/SSL/SSO/monitoring) and does **not** embed infra knowledge.
- **petard** — backup-operator expert (frontier-independent continuity: operate and
  recover even with the cloud or the frontier down).

The expertise is **resolved in**, the same verb everything else in Hoistable resolves
by. A missing skill is a resolved slot — authored just-in-time or pulled from the public
sphere when an operator's problem needs it, then cached as a recipe. It is never a
hardcoded menu of "the skills we support."

## Build-time is narrowing the universe, not solving it

A naive agent and a naive user, dropped in front of "deploy this app," face a **huge
universe** of options: every substrate, every deploy topology, every secret backend,
every scaling and operations and backup choice. Swimming through that universe *is* the
cliff.

Making a product hoistable — the develop/build-time act — is the **expert collapse of
that universe** to a small, sane, still-resolved-and-overridable set. Nudge, not lane.

**NARROW ≠ FIX.** Narrowing *reduces the search space* the naive party swims through
while keeping the choice **resolved at the user's runtime** and **overridable**. Fixing
bakes one option in and *deletes* the user's choice. (Recorded failure, 2026-08-13:
hardcoding an app's substrate into its shipped config — `honcho depends_on docker-host`.
That deleted the option space instead of narrowing it, and deleted the user's runtime
choice with it. Backed out.)

## The three ways Hoistable is used

1. **App developer shipping a product — the skill builder ("WiX++++").** They invoke
   the hoistable skill to *generate* a single distributable deployment skill that
   packages hoistable + their app into a release bundle. That one skill self-extracts
   the hoistable harness and does the whole install / config / clone-or-fork / deploy on
   the target. They may or may not index with hoistable. **Self-contained.**

2. **User hoisting an app.** Uses the hoist skill / index to hoist an app — whether the
   app was hoisted before or not — from the index, from source, or from a URL. Ends at a
   deployed, operable system. This is `brew install` (found) or brew-author (never
   distributed hoistably; hoist builds the config *with* the user).

3. **Developer integrating hoistable into their own distributable.** For use with #2,
   through whatever distribution channel they choose, via **pinned-pull** — explicitly
   **NOT** a single self-extracting skill. Point don't embed; the config pins operator
   versions and pulls them from the Layer 0 release.

Modes 1 and 3 are both developer-facing and both end at a mode-2 hoist on the user's
side; they differ in the *artifact*: mode 1 is one self-contained skill that carries the
harness, mode 3 is a config that references a pinned harness.

## Honest built / recorded status (re-derive; do not trust as frozen)

- **Mode 2** — recorded (README "hoist: the skill you invoke") and **built**: the hoist
  skill resolves an app path→index→URL and authors a config for un-hoisted apps (its
  neutral core `hoist.py`/`author.py` carry the resolver and the first-draft helper).
  Web-search discovery is the one open extension point.
- **Mode 3** — recorded (README "Distribution and repeatability") and **built**: a config
  pins the operator kit by URL+hash and the skill pulls+verifies it (`pins.py`);
  `build_bundle` pins-not-vendors; proven end-to-end on agent-dyno against a real GitHub
  release.
- **Mode 1** — **not built** as a single self-extracting skill. What exists today
  (`build_bundle`) is mode-3's pinned-pull shape, not a self-contained vendored skill.
- The three-mode trichotomy, the meta-skill concept, and build-time-as-narrowing were
  **not previously recorded**; this file is their first capture.

## Open decision (reserved to Baron): mode 1 vendors; the posture pins

Mode 1 self-*extracts* the harness, which means the artifact **carries** it —
vendoring. The build rules deliberately chose the other way: item 270 reversed
adopt-by-copy in favor of pinned-pull (build-rules 4 "federated by pinned version line"
and 6 "point don't embed"). So mode 1 is either:

- **(a)** a sanctioned exception — a self-contained, offline-capable release artifact
  that carries a **pinned snapshot** of the operator kit (repeatable by content hash,
  no network at install), or
- **(b)** still pins-and-pulls at install and is "single skill" only in packaging, not
  in self-containment.

Recommendation: **(a)** — a WiX-style installer that needs the network to fetch its own
guts is not what "ships itself" should mean; carry a pinned, hash-verified snapshot so
the bundle is liftable and offline (build-rule 3, "liftable and complete by reference"),
while staying a *snapshot of a pinned version*, never a fork. Decision is Baron's.

## Where this lives next

- The meta-skill mechanism (an operator *pulling in and composing* a public
  best-practice skill) is not built; today the operators are method files + reference
  code. The smallest honest proof: one operator resolving one real public best-practice
  skill to **narrow** one real product's options at build time, resolved at runtime.
- Mode 1's skill builder (per the decision above) is the other open build.
