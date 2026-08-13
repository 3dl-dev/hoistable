#!/usr/bin/env python3
"""develop: run your own development on a self-hosted open-source app.

The dev-team lifecycle for a hoisted OSS project. It lets the self-hoster iterate
on the software and manage the relationship with upstream, without getting stuck
on a fork that rots:

  - adopt        set up the tree: a fork (origin = your fork, upstream = the
                 original) or a separate tree (your own origin, upstream tracked).
  - pull_upstream fetch upstream and integrate it, returning clean/conflict so the
                 caller can then run the tests (no silent success on a sync).
  - contribute   start a branch for a change to send back upstream.
  - diverge_report  how far your tree has drifted from upstream (ahead/behind).

Opening the actual pull request is a gh step the develop skill drives; this module
is the git topology, which is the part that must be exact and testable. Harness
agnostic: git, plus gh only for the optional PR. Standard library only.
"""

import argparse
import json
import os
import subprocess
import sys


def _git(repo, *args, check=True):
    return subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True, check=check)


def _remotes(repo):
    out = _git(repo, "remote").stdout.split()
    return {r: _git(repo, "remote", "get-url", r).stdout.strip() for r in out}


def _current_branch(repo):
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip() or "main"


def adopt(repo, upstream_url, mode="fork", fork_url=None):
    """Set up the tree for development against upstream. Idempotent.
    mode 'fork': origin -> your fork (fork_url), upstream -> the original.
    mode 'separate': origin stays your own tree, upstream -> the original."""
    remotes = _remotes(repo)
    if "upstream" in remotes:
        _git(repo, "remote", "set-url", "upstream", upstream_url)
    else:
        _git(repo, "remote", "add", "upstream", upstream_url)
    if mode == "fork" and fork_url:
        if "origin" in remotes:
            _git(repo, "remote", "set-url", "origin", fork_url)
        else:
            _git(repo, "remote", "add", "origin", fork_url)
    return {"mode": mode, "remotes": _remotes(repo)}


def pull_upstream(repo, branch=None, rebase=False):
    """Fetch upstream and integrate its branch into the current tree. Returns
    whether it came in clean; on conflict the tree is left for the user to
    resolve, and the caller should NOT trust it until the tests pass again."""
    branch = branch or _current_branch(repo)
    _git(repo, "fetch", "upstream", check=False)
    op = ["rebase", f"upstream/{branch}"] if rebase else ["merge", "--no-edit", f"upstream/{branch}"]
    r = _git(repo, *op, check=False)
    return {"clean": r.returncode == 0, "detail": (r.stdout + r.stderr).strip()[-800:]}


def contribute(repo, branch, base=None):
    """Start a contribution branch for a change to send upstream."""
    r = _git(repo, "checkout", "-b", branch, check=False)
    return {"branch": branch, "base": base, "ok": r.returncode == 0,
            "detail": (r.stdout + r.stderr).strip()[-400:]}


def diverge_report(repo, branch=None):
    """How far the tree has drifted from upstream: commits ahead and behind."""
    branch = branch or _current_branch(repo)
    _git(repo, "fetch", "upstream", check=False)
    r = _git(repo, "rev-list", "--left-right", "--count",
             f"upstream/{branch}...HEAD", check=False)
    behind, ahead = (r.stdout.split() + ["0", "0"])[:2] if r.returncode == 0 else ("?", "?")
    return {"ahead": ahead, "behind": behind}


def main(argv=None):
    ap = argparse.ArgumentParser(description="develop: git topology for self-hosting an OSS app")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("adopt")
    a.add_argument("repo"); a.add_argument("upstream_url")
    a.add_argument("--mode", choices=["fork", "separate"], default="fork")
    a.add_argument("--fork-url", default=None)
    p = sub.add_parser("pull-upstream")
    p.add_argument("repo"); p.add_argument("--branch", default=None)
    p.add_argument("--rebase", action="store_true")
    c = sub.add_parser("contribute")
    c.add_argument("repo"); c.add_argument("branch")
    d = sub.add_parser("diverge")
    d.add_argument("repo"); d.add_argument("--branch", default=None)
    args = ap.parse_args(argv)

    if args.cmd == "adopt":
        out = adopt(args.repo, args.upstream_url, args.mode, args.fork_url)
    elif args.cmd == "pull-upstream":
        out = pull_upstream(args.repo, args.branch, args.rebase)
    elif args.cmd == "contribute":
        out = contribute(args.repo, args.branch)
    else:
        out = diverge_report(args.repo, args.branch)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
