---
name: hoist
description: Onboard an app as a running, graded system from its hoistable config, or author that config for an app that has none. The brew of hoistable. Drives the whole flow and never leaves the user at a blank prompt.
---

hoist is a skill you (the agent) run. Point it at an app and get the user to a running,
graded system, whether or not the app was ever distributed hoistably. This is
agent-first: you do the work in-loop; the user never touches a command line.

## Two modes

- **The app has a config already.** Find it the way brew finds a formula, in this
  order: a local path, the index, a GitHub URL, a web search. Then run it.
- **The app has no config.** You author one by reading the repo: understand how it
  builds, tests, and deploys, and what a clean-target run needs, then write the config
  (schema in `envelope/README.md`). This is judgment work and adapts to any language or
  shape. `hoist/author.py` drafts a first cut for common cases (hermetic test repos,
  docker-compose) with `_TODO`s where a machine cannot infer intent; treat it as a
  starting point you complete, not the author.

Either way you reach a deployed, graded system, or an honest reason you did not.

## Drive, never a blank prompt

Onboarding is driven, not a menu. You take the wheel; the user never sees a prompt with
nothing to do:

1. **Resolve the config** — discovery above. (The neutral core `hoist/hoist.py` carries
   the local-path resolver; index and URL are its extension points. You call the core;
   you never leave that to the user.)
2. **Know early.** Run preflight first, which deploys nothing — invoke the neutral-core
   grader in preflight-only mode (`envelope.py --until preflight`). If it says
   cannot-build, stop at the door and give the user the named reason.
3. **Deploy and grade.** If feasible, run the full pass, invoking the neutral-core grader
   (`envelope.py`), which *enforces* isolation, the honest transfer grade, and teardown.
   Report the honest outcome: built, honest-failure (say what did not transfer), or
   cannot-build.
4. **Hand off** to the operators the config includes: develop, sysop, petard.

## Invariants hoist carries

- **Non-destructive onboarding.** hoist never re-runs an app's own singular
  deployment. Every hoist lands in a fresh isolated namespace the runner owns, and is
  refused if a deploying profile declares no isolation. See README.md.
- **No silent success.** The install is graded on the real target; one that cannot say
  it worked says what did not.
- **Pinned operators.** The config pins operator versions by URL from the Layer 0
  release, so the same config resolves the same operators every time.

## The skill is the channel; the core enforces

This `SKILL.md` is the hoist skill in its Claude Code form; the same method ports to
other *agent* harnesses behind a thin adapter — the channel is a skill an agent runs,
never a command line. The neutral core is `envelope.py` plus `hoist.py` (standard
library, no harness assumptions) and the config schema: the small code you call to
*enforce* the invariants, not a driver a user runs.
