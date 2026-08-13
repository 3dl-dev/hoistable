---
name: preflight
description: Scope a deployment with the user and tell them early whether it will work, deploying nothing. Emits the scoped plan and a feasibility verdict for sysop.
---

preflight is the human-in-the-loop operator. It runs before anything is deployed and
hands sysop a settled plan, so sysop never re-litigates the shape of the deployment or
is the first to hit a blocker.

## Scope with the user

Fix the dimensions of the deployment by asking, not assuming:

- scale (how much traffic, how many users)
- tenancy (single- or multi-tenant)
- environment (dev or prod)
- infra target (local VM, AWS, Azure, DigitalOcean, an existing cluster)
- which external skills the target needs (the infra sysop will compose)

Read the app's config surface (contract A, from develop) to know which knobs are yours
to turn. Choose or parametrize a profile in the config from the answers.

## Know early, deploy nothing

Run the know-early pass:

    python3 envelope/envelope.py <config> --profile <chosen> --until preflight

It checks the required binds, the feasibility probes (platform, versions, deps,
reachability, secret availability), and that the target is clean, then stops before
deploy. Its verdict is feasible or cannot-build, with the blocker named. Give the user
that verdict at the door, not three services deep.

## Emit

Hand sysop the scoped plan (the chosen profile and its knob values), the app's artifact
and config surface carried forward, and the feasibility verdict. That is contract B.
