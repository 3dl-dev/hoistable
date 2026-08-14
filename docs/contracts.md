# The operational contracts

The operators (develop, preflight, sysop, petard) are reusable only because of the
interfaces between them. Name the interfaces and the operators become genuinely
product-agnostic. Leave them implicit and every product re-smuggles its own knowledge
into the generic machinery.

The operators form a chain, develop to preflight to sysop to petard, and there is one
contract per adjacent pair. A project specifies a contract only when both of its
operators are present: a product with no develop operator has no develop-to-preflight
contract to write, and its chain begins at preflight.

Alongside the chain there is one shared artifact both sysop and petard bind to: the
substrate handle (see "The substrate handle" below). sysop deploys the app into it;
petard harvests ground truth out of it. It is not a contract between one pair, it is
the place the work happens, resolved per target.

## Contract A: develop to preflight (the deployable artifact)

What feature work emits and deployment scoping consumes.

- **develop writes it**: the built artifact plus its config surface, the set of knobs
  a deployment is allowed to turn. It names what is configurable and what is fixed.
- **preflight reads it**: it reads the config surface to learn what is scopable, then
  carries the artifact forward to sysop as part of the scoped plan. sysop deploys
  against the surface and does not reach past it into the product's internals.

## Contract B: preflight to sysop (the scoped deployment plan)

The boundary between deciding the deployment and executing it.

- **preflight writes it**: after working with the user, it fixes the dimensions of the
  deployment, scale, single- vs multi-tenant, dev vs prod, the infra target, the
  isolation strength the deploy needs (a same-host namespace, or an environmental
  substrate where a deploy cannot reach host state), and which external skills the
  deployment will need. This is the human-in-the-loop decision, made once and written
  down. It carries develop's artifact and config surface forward, so sysop has a single
  inbound handoff. It also carries a feasibility verdict: preflight probed the target
  for the known long-tail gaps, including which isolation substrate the target offers,
  and recorded what will work and what will block, so sysop is not the first to
  discover a blocker. A required isolation strength that no substrate on the target can
  meet is one of those blockers, named at the door.
- **sysop reads it**: it takes the plan as given and chases it down. It does not
  re-litigate the dimensions; those were settled at preflight.

## Contract C: sysop to petard (the operational index)

A continuously refreshed index of the operational surface, exported to the local,
lights-out layer.

- **sysop maintains it**: keeping the petard's corpus fresh is part of sysop's job. It
  is a backup responsibility, not a nicety. The corpus must include runbooks
  executable *without a frontier model*. Lights-out capability is a run-time output
  requirement, not an afterthought: if sysop does not emit model-free runbooks, the
  petard has nothing to fall back to.
- **petard reads it**: the local model does not reason its way to a command. It pulls
  the current facts (command surface, board and schema shapes, doc locations,
  runbooks) from this corpus and translates the operator's intent into the shape of
  what is needed.
- **The corpus is the asset**: the local model is weak, swappable, almost incidental.
  What determines whether the petard works is the freshness and coverage of this
  index.
- **Harvested through the substrate handle**: the ground truth petard indexes lives in
  the running instance, and the instance may run inside a resolved substrate (a
  container, a VM, a cluster Job), not on the host. So the harvest that keeps the corpus
  fresh runs through the same substrate handle sysop deployed into: a `--help` dump or a
  schema introspection is an `exec` into the substrate, not a host subprocess. Without
  the handle, contract C has no path to the ground truth of a sandboxed deploy.

## The petard grounding invariant

**The petard's corpus must be generated from ground truth, never hand written, and its
output must be retrieval grounded.**

- **Generated, not authored**: build the corpus from `--help` dumps, live schema
  introspection, and runbook harvests. Hand-written docs drift. A drifted doc makes the
  petard confidently hand you a stale flag, which is worse than no petard. (Concrete
  cost seen in practice: a hand-maintained flag table documented `--parent` for four
  months after the real flag became `--parent-id`; every operator who trusted the table
  created orphans.)
- **Retrieval grounded, not generative**: the petard constructs its answer from the
  pulled text, and is forbidden from generating command shapes from parametric memory.
  Its strength is aggregating and translating facts faster than a human can, not
  inventing them.

A petard that lies is worse than no petard. This invariant is what keeps it honest.

## The substrate handle

Where a hoist runs is not a dependency, it is a resolved bind. The same verb the rest
of Hoistable runs on (a config ref resolves, operator pins resolve, a secret resolves
on the target) applies to isolation: a profile names the strength it needs, and you (the agent) resolve the strongest
rung the target offers, or report cannot-build. You resolve it in-context, in the user's
session; the contract is four capabilities you provide with the target's own tooling:

    provision  ->  stand up a throwaway place to run (or nothing, for the host).
    exec(cmd)  ->  run one step there, get its result.
    teardown   ->  destroy it; a hoist leaves the target as it found it.
    workroot   ->  the base dir a clone and deploy happen under, in that place.

- **The host is the floor rung**: exec is a plain subprocess, and the isolation is only
  as strong as the config's own declared namespace, so a deploy that ignores it can
  still reach host state. A stronger rung (docker-in-docker today; rootless podman, a
  user-namespace sandbox, a burnable VM, a cluster Job next) runs the steps somewhere a
  deploy cannot reach host state, whatever the config declares. A new rung is one you stand
  up in the loop from the target's own tooling (docker, kubectl, a cloud CLI), never
  shipped code, and the knowledge of how to drive it is yours in-context (point, don't
  embed).
- **Both operators bind to it, which is why it is shared, not paired**: sysop resolves
  it and deploys into it (the isolation is environmental, not left to a config to
  honor); petard harvests ground truth out of it (contract C). One handle, two
  operators.
- **The strength is reported, never assumed**: the guarantee is only as strong as the
  rung that resolved. A resolution records which rung it got, and a replay re-probes and
  re-resolves rather than trusting that record (see the resolution store,
  `hoist/resolutions.py`): the environment is re-derived, never remembered.
