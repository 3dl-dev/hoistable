---
name: develop
description: Extend a hoistable app by adding features through its manifest and handlers, and emit the deployable artifact and its config surface for preflight and sysop.
---

develop is the operator for products that recipients extend. A fixed tool does not need
it; an extensible framework does.

## Extend through manifest and handlers

Add a feature by declaring it in the app's manifest and implementing its handlers, not
by editing the generic machinery. The manifest plus handlers are the app's extension
mechanism and the substance of what the config carries. Keep the neutral core
untouched: a new capability is a new handler in an existing slot, not a new slot
(converge, do not accrete).

## Emit the artifact and its config surface

develop's output is contract A: the deployable artifact plus its config surface, the set
of knobs a deployment is allowed to turn. Name what is configurable and what is fixed.
preflight reads the surface to learn what is scopable; sysop deploys against it and does
not reach past it into the product's internals.

## Ship source, not binary

Per the build rules, what develop emits is a reference build: a spec, a generator, and
an acceptance test, regenerable and verified. The acceptance test is exactly what the
envelope runs on the target to grade the install honestly, so develop and the honest
grade are two ends of the same thing.
