---
name: sysop
description: Take preflight's scoped plan and stand the app up on the target, then operate it. Composes external infra skills, owns secrets, keeps petard's corpus fresh. Deploys into an isolated namespace, never the app's own.
---

sysop takes the settled plan and chases it down: deploy, operate day to day, and be the
one who owns the secrets.

## Deploy, in isolation

Deploy by running the config's chosen profile through the envelope, which owns a fresh
namespace per hoist (its own name, ports, storage), verifies the namespace is empty,
and can tear it down:

    python3 envelope/envelope.py <config> --profile <chosen>

sysop never re-runs the app's own singular deployment. That is the non-destructive
onboarding invariant, enforced by the runner: a profile that deploys must declare
isolation or it is refused. Hoisting an app is deploying an isolated copy, not
re-asserting the one instance the app assumes it is.

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
