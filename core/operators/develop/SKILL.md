---
name: develop
description: The dev-team lifecycle for a self-hosted open-source app. You (the agent) understand how to iterate on it and test it, fork it or keep a separate tree, pull from upstream (verified against the tests), and contribute back when the user chooses.
---

develop is the operator for people who run their own copy of an open-source project
and want to keep developing it. **You do this work with judgment** -- every project's
build, test loop, and hosting differ, and adapting to them is the job. The scripts
below are tested reference builds for the exact, safe git mechanics; use them when they
fit, adapt or regenerate them when they do not (build-rule 1). What is yours is the
understanding: reading an unfamiliar codebase, deciding fork vs separate tree,
resolving a real merge conflict, judging whether a change is worth upstreaming.

## Understand how to iterate and test

Read the project the way a new contributor would: its README, CONTRIBUTING, Makefile,
CI config, and test files. Learn how it is built, how it is tested, and where the
contribution path is, in the project's own terms. `guide.py <repo>` gives you a first
harvest of that from ground truth (test commands, targets, CONTRIBUTING, CI) -- a
starting point you refine by reading, not a substitute for reading.

## Own the tree: fork or keep it separate

Decide with the user which they want, then set the remotes up. `tree.py adopt` does it
safely (fork: origin = your fork, upstream = original; or separate: your own origin,
upstream tracked). Fork when they mean to contribute back; separate tree when they mean
to diverge privately.

## Pull from upstream, then verify

`tree.py pull-upstream` fetches upstream and integrates it, reporting clean or conflict
and leaving a conflict for you to resolve with judgment rather than smearing over it. A
sync is not done until the tests pass again: after a pull, run the project's acceptance
(the same checks the envelope grades) before you trust it. Use `tree.py diverge` to see
how far ahead/behind upstream the tree has drifted.

## Contribute back, on the user's say

`tree.py contribute` starts a branch for a change. Opening the pull request is the
user's call, never automatic -- you drive `gh pr create` only when they ask. Keeping a
separate tree and never upstreaming is an equally valid path.

## What develop emits

Contract A: the deployable artifact and its config surface, the knobs a deployment may
turn versus what is fixed. And per build-rule 1, a change ships as a reference build
with its own acceptance test, which is exactly what the envelope runs on the target to
grade the install. develop and the honest grade are two ends of the same thing.

## Where the code stays load-bearing

The git mechanics are scripted because a wrong merge or remote is worse than an
inflexible one, and because they are worth testing. The judgment around them is yours.
This is the split across all of hoistable: agents author and adapt (the long tail);
code enforces and falls back (the git safety, and petard when the frontier is down).
