---
name: hoist
description: Get an app running and honestly graded on this machine, from a hoist skill someone shared or by authoring the recipe yourself. Agent-first: you do the work in this session, with ordinary tools. Nobody runs a command line, and there is nothing to fetch or install of ours.
---

hoist is a skill you (the agent) run, in the user's session, with tools already on the
target (git, the container runtime, a shell). Point it at an app and get the user to a
running, graded system, whether or not the app was ever packaged as a hoist skill. You do
the work here, in context; the user never touches a command line, and there is no runtime
of ours to fetch or run.

## Two modes

- **You were handed a hoist skill.** Someone shared an `<app>.hoist.SKILL.md`. It is
  self-contained: it carries the app's recipe and this same honest-grade discipline.
  Follow it.
- **The app has no recipe yet.** Author one by reading the repo: how it builds, tests, and
  deploys, and what a clean-target run needs, the binds it depends on, how it must be
  isolated, the bringup steps, the health checks, and the acceptance checks that prove it
  actually works. This is judgment; ground the acceptance in what "it works" means for THIS
  app, a machine cannot infer that. Then run the discipline below.

Either way you reach a deployed, graded system, or an honest reason you did not.

## The honest-grade discipline (same order every time; the order is the guarantee)

You carry this out yourself, in-session, against this target:

1. **Binds gate.** Probe each required capability on the host. A missing required one is
   **cannot-build**: name it, stop, deploy nothing.
2. **Resolve the isolation.** A deploy must never touch host state. If the recipe needs an
   environmental sandbox (docker-in-docker, a throwaway VM), stand up the strongest one the
   target offers and work inside it; otherwise use the recipe's host-floor namespace (fixed
   project name, OS-chosen free ports, named volumes). A deploying profile that declares no
   isolation is refused. Resolve this against the target; never assume it.
3. **Preflight (deploy nothing).** Clone, run the cheap probes. A required blocker is
   cannot-build, named, at the door.
4. **Deploy (the install gate)** in the isolated namespace or sandbox only, never onto a
   live host.
5. **Health, then held-back acceptance.** Count health N of M; only if fully up, run the
   acceptance checks against the running instance. Their pass fraction is the honest
   transfer score, whether it really works here, not just came up.
6. **Land it, or clean up honestly.** The objective is a running, usable app. On success,
   LEAVE it running in its isolation (that is what the user asked for, not residue) and note
   where it is reachable. Tear down only if it failed (clean up the broken instance), or if
   you were asked merely to prove it would work. Either way, leave nothing outside the app's
   own isolation.
7. **Report one honest line:** built (transferred N of M, running at [where]), honest-failure
   (say what did not transfer; partial instance torn down), or cannot-build (name the missing
   bind or isolation strength). Never let a design read as a running system.

## Hand off

Point the user at the operators the recipe includes, develop, sysop, petard, so they can
use, operate, and keep the app running, not merely have it installed.

## The skill is the channel

This is agent-first: you do it in the user's session. There is no neutral-core runtime to
fetch, no CLI, no pinned toolchain. The discipline above is the whole of it, and you carry
it out with the tools already on the target. The method ports to any agent harness; it is
prose an agent follows, never a command a user runs.
