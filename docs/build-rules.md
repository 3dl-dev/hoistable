# Build rules

How Hoistable's operators and the skills they produce get built. First practiced in
`agent-dyno`; kept here because they constrain how the four operators (develop,
preflight, sysop, petard) are written.

## 1. Ship source, not binary

The source of a tool is three parts: a **spec** (what it must do: inputs, outputs,
method, determinism, limits), a **generator** (the prompt or method that turns the
spec into code), and an **acceptance test** (the spec made executable, checking a
build against a known answer). The checked-in code is a *reference build*:
regenerable from the spec, verified by the test, deletable. Publishing only the
code publishes the binary.

## 2. Neutral core, thin adapters

The core is agnostic to harness, config, and agent. Anything harness-specific lives
behind a thin adapter that emits a common schema. A new harness is a new adapter,
never a fork of the core. A new model plugs in through a registry, never a hardcoded
ID.

## 3. Distributable: liftable and complete by reference

Each unit can be lifted out of the repo it was born in and run wherever its references
resolve. It names everything it needs: an operator names the external skills it
composes (rule 6); a config names its operator pins (rule 4). A small tool with no
dependencies inlines its whole method and runs cold; a larger unit completes itself by
reference instead of inlining the world. Either way the test is the same: lift it out,
resolve its references, and it runs. If it cannot, it is not done. This is Hoistable's
own thesis applied to its parts: ship a recipe that pulls itself up, not a binary that
inlines everything.

## 4. Federated by a pinned version line

What Hoistable produces isolates itself from upstream change, so one repo upgrading
does not break another. A Layer 2 config gets that isolation by **pinning a version**
of each operator skill, where a pin is just a URL into the Layer 0 release.
Repeatability comes from the pin: the same URL resolves to the same operators every
time, and a Layer 0 release does not touch a config until its owner bumps the pin.
There is one pinned version line, not one per operator. Configs do not vendor operator
copies: vendoring is bad ergonomics and a vendored copy forks and rots, which is the
drift the petard invariant exists to prevent, turned on the operators themselves. A
pin is a URL, and URLs are enough. Nothing is uploaded or shared unless the owner
chooses.

## 5. Converge, do not accrete

A new capability lands in exactly one existing slot. If it needs a brand-new slot,
stop: that is the signal you are accreting, not converging. Fewer, load-bearing
slots beat many thin ones. (The `rigging` repo failed this test and was folded back
in here.)

## 6. Point, don't embed

An operator composes external skills for anything it is not the authority on, and does
not internalize that knowledge. sysop does not learn AWS, Azure, SSL, or SSO; it points
at the relevant third-party skills and jams them together. The operator owns the
orchestration, the secrets, and the glue. Maximize reuse of skills that already exist;
write new method only for the seam Hoistable is uniquely responsible for.

## 7. No silent success

A distribution reports honestly whether it worked, on the target where it ran, at two
moments. Before the deploy, preflight probes the target for the known long-tail gaps
(platform, versions, dependencies, reachability, secret availability) and predicts
feasibility, so the user learns at the door whether this is going to work rather than
three services deep. After it runs, the config rebuilds its acceptance test on the
actual target and prints a transfer score per check, saying plainly what did not
transfer. A config that reports "installed" without grading is lying by omission. That
normalized score is also the gradeable output a downstream measure (a leaderboard, the
dyno) aggregates across harness, model, and context; the config emits the number and
never depends on the grader.

## 8. Plain copy

No em-dashes. No AI intensifiers ("real", "genuine", "leverage", "seamless"). Plain,
honest prose that states what is true, including what is not yet built.
