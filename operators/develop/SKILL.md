---
name: develop
description: The dev-team lifecycle for a self-hosted open-source app. Understand how to iterate on it and test it, fork it or keep a separate tree, pull from upstream (verified against the tests), and contribute back when the user chooses.
---

develop is the operator for people who run their own copy of an open-source project
and want to keep developing it, not just operate a frozen build. It is what keeps a
self-hoster off a fork that rots: your own tree that can still track upstream and give
back to it. It is the biggest operator, because "run your own dev team on this project"
is a big job. It is harness-agnostic: git, plus gh only for the optional pull request.

## Understand how to iterate and test

    python3 operators/develop/guide.py <repo>

Before changing anything, learn the project's own dev loop from its ground truth (the
petard discipline: generated, never authored). guide harvests the test commands,
build/run targets, the CONTRIBUTING path, and the CI workflows from the Makefile,
package scripts, CI config, and the test files themselves. It tells the user how to
test and where the contribution path is, in the project's own terms.

## Own your tree: fork or keep it separate

    python3 operators/develop/tree.py adopt <repo> <upstream_url> --mode fork --fork-url <url>
    python3 operators/develop/tree.py adopt <repo> <upstream_url> --mode separate

- **fork**: origin is your fork, upstream is the original. For contributing back.
- **separate tree**: your own origin, upstream tracked for pulls. For a private
  divergence you do not intend to send back.

## Pull from upstream, verified

    python3 operators/develop/tree.py pull-upstream <repo> --branch main

Fetch upstream and integrate it. It reports clean or conflict honestly and, on
conflict, leaves the tree for you to resolve rather than smearing over it. A sync is
not done until the tests pass again: after a pull, run the project's acceptance (the
same checks the envelope grades) before you trust it. No silent success on an upstream
merge either.

    python3 operators/develop/tree.py diverge <repo>     # how far ahead/behind upstream

## Contribute back, when the user chooses

    python3 operators/develop/tree.py contribute <repo> <branch>

Start a branch for a change to send upstream. Whether to open the pull request is the
user's call, never automatic; the develop skill drives `gh pr create` only on their
say-so. Keeping a separate tree and never upstreaming is an equally valid path.

## What develop emits

Contract A: the deployable artifact and its config surface, the knobs a deployment may
turn versus what is fixed. preflight reads the surface to scope a deployment; sysop
deploys against it. And per build-rule 1, a feature ships as a reference build with its
own acceptance test, which is exactly what the envelope runs on the target to grade the
install. develop and the honest grade are two ends of the same thing.
