# The operational contracts

The operators (develop, preflight, sysop, petard) are reusable only because of the
interfaces between them. Name the interfaces and the operators become genuinely
product-agnostic. Leave them implicit and every product re-smuggles its own knowledge
into the generic machinery.

The operators form a chain, develop to preflight to sysop to petard, and there is one
contract per adjacent pair. A project specifies a contract only when both of its
operators are present: a product with no develop operator has no develop-to-preflight
contract to write, and its chain begins at preflight.

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
  deployment, scale, single- vs multi-tenant, dev vs prod, the infra target, and which
  external skills the deployment will need. This is the human-in-the-loop decision,
  made once and written down. It carries develop's artifact and config surface forward,
  so sysop has a single inbound handoff. It also carries a feasibility verdict:
  preflight probed the target for the known long-tail gaps and recorded what will work
  and what will block, so sysop is not the first to discover a blocker.
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
