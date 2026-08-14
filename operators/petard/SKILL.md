---
name: petard
description: The no-frontier operational fallback. When the frontier model is down and credits are out, you still get the exact command to run, grounded in your system's own ground truth. petard composes arlo; it never invents a command.
---

petard keeps you able to operate when the frontier model is down or rate limited. The bar:
you type your own words ("bounce the workshop instances", "reset a password", "restart"),
and you get back the real command to run, from your system's own ground truth. If it
depends on the thing that is down, it is not a petard.

petard does not carry that engine itself. It **composes arlo**, a real, local operator
that runs on its own power and network. In the user's session, when the frontier is down,
you invoke arlo:

    arlo "restart the cluster"

and arlo answers with the grounded command, or says it has no confident match, never
inventing one. That is the whole of petard: resolve arlo and hand the user's words to it.

## Resolve arlo (pin, do not vendor)

arlo is source of truth and iterates on its own. petard pins a released version and
composes it; it does not copy arlo's code into hoistable. The pin is in `pin.json`
(arlo v0.1.0, `3dl-dev/arlo`).

Install it in the receiver's environment the way any skill installs:

    /plugin marketplace add 3dl-dev/arlo
    /plugin install arlo@arlo

or use the `arlo` CLI directly. Either way, arlo runs in the user's session, on ground
truth harvested from their live system. hoistable never runs arlo's engine in our process;
that would be building software instead of composing a skill.

## Why compose, not embed

The petard invariant (independent of whatever is down) and the "build the skill, not the
software" rule point the same way: arlo is a runtime that must not depend on us, and we
must not import its library to run it here. We pin it, and the user's agent invokes it
there.
