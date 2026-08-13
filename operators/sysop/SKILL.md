---
name: sysop
description: Take preflight's scoped plan and stand the app up on the target, then operate it. Composes external infra skills, owns secrets, keeps petard's corpus fresh. Deploys into a resolved isolation substrate (a same-host namespace, or an environmental sandbox where a deploy cannot reach host state), never the app's own.
---

sysop takes the settled plan and chases it down: deploy, operate day to day, and be the
one who owns the secrets.

## Deploy, in isolation

Deploy by running the config's chosen profile through the envelope:

    python3 envelope/envelope.py <config> --profile <chosen>

sysop never re-runs the app's own singular deployment. That is the non-destructive
onboarding invariant, enforced by the runner: a profile that deploys must declare
isolation or it is refused. Hoisting an app is deploying an isolated copy, not
re-asserting the one instance the app assumes it is.

Isolation is resolved, not fixed. The profile names the strength it needs, and the
runner resolves the strongest rung the target offers:

- **The host floor**: the envelope owns a fresh namespace per hoist (its own name,
  ports, storage), verifies the namespace is empty, and tears it down. This is a
  same-host copy, so the isolation is only as strong as that namespace.
- **An environmental substrate** (`isolation.require: "environmental"`): the deploy
  runs inside a throwaway container, VM, or cluster Job where it cannot reach host
  state whatever the config declares, resolved down a ladder (docker-in-docker today).
  Use it for an app you have not hoisted before, where a fresh clone is not a clean
  target. If the target offers no substrate that meets the required strength, that is a
  cannot-build, named, deploying nothing.

The substrate is a resolved bind like any other (see docs/contracts.md, "The substrate
handle"). It is also the handle petard harvests through, so the deploy sysop stands up
is reachable by the lights-out layer even when it lives in a container or a cluster.

## Point, don't embed

sysop is not the authority on AWS, Azure, DigitalOcean, SSL and certs, SSO, or security
monitoring. It points at the relevant third-party skills and composes them. It writes
new method only for the seam hoistable owns: the orchestration, the secrets, and the
glue. The config's binds name what the target must provide; sysop resolves each against
the user's setup or provides its own.

## Own the secrets

sysop owns secret handling, dovetailing with whatever the user has (a vault, a cloud
secret manager, env files) or providing its own. A secret is a bind, resolved on the
target, never carried in the config.

## Keep petard fresh

Keeping petard's corpus current is sysop's backup job, not a nicety. After a deploy and
after any change to the command surface, rebuild the corpus from ground truth (see the
petard operator). That is contract C.
