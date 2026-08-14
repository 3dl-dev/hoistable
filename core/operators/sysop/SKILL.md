---
name: sysop
description: Take preflight's scoped plan and stand the app up on the target, then operate it. Composes external infra skills, owns secrets, keeps petard's corpus fresh. Deploys into a resolved isolation substrate (a same-host namespace, or an environmental sandbox where a deploy cannot reach host state), never the app's own.
---

sysop takes the settled plan and chases it down: deploy, operate day to day, and be the
one who owns the secrets.

## Deploy, in isolation

Deploy by following the honest-grade discipline in this session: stand up the resolved
isolation, then run the config's chosen profile's bringup inside it. You do this in
context with ordinary tools; there is no runner of ours to invoke.

sysop never re-runs the app's own singular deployment. That is the non-destructive
onboarding invariant you hold: a profile that deploys must be isolated or it is refused.
Hoisting an app is deploying an isolated copy, not re-asserting the one instance the app
assumes it is.

Isolation is resolved, not fixed. The profile names the strength it needs, and the
runner resolves the strongest rung the target offers:

- **The host floor**: you own a fresh namespace per hoist (its own name, ports,
  storage), verify it is empty before deploy, and tear it down after. This is a
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

## Author a rung just-in-time

The rungs are a cache, not a menu (docs/ops-substrate.md). When a config needs an
isolation substrate and no cached rung resolves for this target, sysop AUTHORS one.
This is the loop, and you are the one who runs it -- there is no separate automation
to build, because you doing this and a dispatched sysop agent doing this are the same
thing. Do not try to pre-mint every contingency into a script; interrogate the target
here, in the loop:

1. **Interrogate the target.** Probe what isolation the host actually offers -- a
   container daemon, a reachable cluster, user namespaces, a burnable VM, a cloud
   account. Do the messy inference now; do not assume.
2. **Stand the isolation up against what you found.** Resolve it in-context: compose the
   target's own tooling (docker for a throwaway container, kubectl for a cluster Job, a
   cloud CLI for a burnable VM) into an isolation you can provision, exec inside, and tear
   down leaving no residue. Point, don't embed: own only the glue, and do it here in the
   loop, not as a shipped adapter.
3. **Grade it against reality.** Run a real workload through the isolation, verify it came
   up, and verify teardown leaves no residue (the non-destructive invariant). An isolation
   you have not graded against a real workload is not done.
4. **Label its honest strength.** Never claim a guarantee the rung does not provide.
   k3s isolates the workload but runs its deploy driver on the host, so it is
   `cluster`, not host-safe `environmental`. An honest weaker rung beats a dishonest
   strong label; do not wire a rung into the environmental ladder unless it earns it.
5. **Surface cost, then cache.** Local or standing infra is $0; a burnable cloud rung
   has a price -- estimate it, gate it by policy, never spend silently. A graded rung
   becomes a cached recipe (the resolution store) so the next operator pulls it instead
   of re-authoring.

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
