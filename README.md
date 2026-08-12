# Hoistable

Software that ships itself.

Software has been shipped as a prebuilt artifact: build once, distribute the
binary, and eat the long tail of per-environment gaps (config drift, platform
quirks, "works on my machine") as recurring cost. Hoistable inverts that. The unit
of distribution is a **skill that hoists the instance into place per install**: it
clones the repo, runs the configuration, does the deployment, and fills the Pareto
long-tail gaps that used to make distribution expensive. You ship the recipe, and
the software pulls itself up by its own bootstraps.

Hoistable is the property and the promise: hand over a recipe, and the software
raises itself into a running system anywhere.

## The three operators

Reusable, harness-agnostic, product-independent. A per-product skill is a thin
recipe over these:

- **devops** (build time): clone, configure, deploy, and hand off operational
  state. Its output includes runbooks that run without a frontier model.
- **sysops** (run time): consume the handoff and operate the deployed system. Its
  backup job is keeping the LOM's corpus fresh.
- **LOM** (lights-out management for the operator's practice): a local, always
  reachable retrieval-and-translation layer that keeps *you* able to act when the
  frontier stack is down or rate limited. Not autonomous ops. It pulls facts from a
  local corpus and translates intent into the shape of the command. Independent
  power and network path, like a server's management board: if it depends on the
  thing that is down, it is not a LOM.

## The two contracts

What makes the three operators reusable instead of re-smuggling product knowledge
into each skill. Both are first-class artifacts, not per-skill details. See
[docs/contracts.md](docs/contracts.md).

1. **devops to sysops**: the operational handoff state.
2. **sysops to LOM**: the continuously refreshed operational index.

## How it ships

The primary channel is a **skill**. A hoistable project distributes itself as a
skill: installing the project means installing a skill, and invoking it hoists the
instance into place (devops), operates it (sysops), and carries the local fallback
(LOM). The skill is the **bootstrap**, the minimal portable thing you install that
pulls the full project up after it.

The skill is self-contained: it bakes in the operator method plus the project's
manifest and handlers, so it has no runtime dependency back on this repo. This
repo's operator skills are the **generators**; a project's distribution skill is the
self-contained **reference build** it emits.

A `SKILL.md` is the Claude Code adapter of this channel, not the whole of it. The
neutral core is a self-contained recipe that hoists; other harnesses package it
their own way. Skill is the primary channel, not the only one.

Two constraints carry over: the LOM ships inside the skill, but its execution path
stays frontier-independent (a fallback that needs the frontier model is not a
fallback); and Hoistable is its own first consumer, distributing its operators as
skills.

## Build rules

How the operators get built ([docs/build-rules.md](docs/build-rules.md)): ship
source not binary (spec + generator + acceptance test); neutral core, thin adapters;
self-contained; federated, no dependency; converge don't accrete; plain copy. First
practiced in agent-dyno.

## Relation to Agent Dyno

Different jobs, shared build rules. Agent Dyno **measures** how efficiently a harness
turns tokens into surviving work. Hoistable **manufactures and operates**. The
relation is one-way: the dyno can measure a Hoistable run; Hoistable never depends on
the dyno.

## Status

Founding spec. The thesis, the three operators, and the two contracts are captured.
The operators themselves, the manifest-and-handlers extension mechanism, and the
acceptance tests are not built yet.
