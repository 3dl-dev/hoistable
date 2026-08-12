# Build rules

How Hoistable's operators and the skills they produce get built. First practiced in
`agent-dyno`; kept here because they constrain how the three operators are written.

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

## 3. Self-contained and distributable

Each unit carries its full method inside itself. It runs cold, with no install step
beyond the standard library, and is not pinned to the repo it was born in. If it
cannot be lifted out and run elsewhere as-is, it is not done. (This is Hoistable's
own thesis applied to its parts.)

## 4. Federated by default, no dependency

What Hoistable produces is adopted by copying, not by a build-time link. One repo
upgrading does not break another. Nothing is uploaded or shared unless the owner
chooses.

## 5. Converge, do not accrete

A new capability lands in exactly one existing slot. If it needs a brand-new slot,
stop: that is the signal you are accreting, not converging. Fewer, load-bearing
slots beat many thin ones. (The `rigging` repo failed this test and was folded back
in here.)

## 6. Plain copy

No em-dashes. No AI intensifiers ("real", "genuine", "leverage", "seamless"). Plain,
honest prose that states what is true, including what is not yet built.
