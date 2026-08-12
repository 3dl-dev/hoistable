# The two operational contracts

The three operators (devops, sysops, LOM) are reusable only because of the
interfaces between them. Name the interfaces and the operators become genuinely
product-agnostic. Leave them implicit and every product re-smuggles its own
knowledge into the generic machinery.

## Contract 1: devops to sysops (the operational handoff)

What a build emits and an operator consumes. This is the boundary between build
time and run time.

- **devops writes it**: at the end of clone, configure, deploy, it produces the
  operational state a run-time operator needs. Where things live, how to reach
  them, how to check health, how to restart, what the known failure modes are.
- **sysops reads it**: it does not rediscover the system; it consumes the handoff.
- **Lights-out requirement**: the handoff must include runbooks executable *without
  a frontier model*. Lights-out capability is a build-time output requirement, not
  a run-time afterthought. If devops does not emit model-free runbooks, the LOM has
  nothing to fall back to.

## Contract 2: sysops to LOM (the operational index)

A continuously refreshed index of the operational surface, exported to the local,
lights-out layer.

- **sysops maintains it**: keeping the LOM's corpus fresh is part of sysops's job.
  It is a backup responsibility, not a nicety.
- **LOM reads it**: the local model does not reason its way to a command. It pulls
  the current facts (command surface, board and schema shapes, doc locations,
  runbooks) from this corpus and translates the operator's intent into the shape of
  what is needed.
- **The corpus is the asset**: the local model is weak, swappable, almost
  incidental. What determines whether the LOM works is the freshness and coverage
  of this index.

## The LOM grounding invariant

**The LOM's corpus must be generated from ground truth, never hand written, and its
output must be retrieval grounded.**

- **Generated, not authored**: build the corpus from `--help` dumps, live schema
  introspection, and runbook harvests. Hand-written docs drift. A drifted doc makes
  the LOM confidently hand you a stale flag, which is worse than no LOM. (Concrete
  cost seen in practice: a hand-maintained flag table documented `--parent` for four
  months after the real flag became `--parent-id`; every operator who trusted the
  table created orphans.)
- **Retrieval grounded, not generative**: the LOM constructs its answer from the
  pulled text, and is forbidden from generating command shapes from parametric
  memory. Its strength is aggregating and translating facts faster than a human can,
  not inventing them.

A LOM that lies is worse than no LOM. This invariant is what keeps it honest.
