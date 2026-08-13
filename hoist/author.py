#!/usr/bin/env python3
"""hoist author: draft a Layer 2 config for an app that has none.

This is the second mode of the brew: when an app was never distributed hoistably,
hoist builds the config with the user, making them its author. This module does
the mechanical first draft by inspecting the repo; the hoist skill refines it with
the user (naming the acceptance checks a machine cannot infer).

It handles the two shapes we have seen:
  - a project whose tests are hermetic (stdlib scripts, no services): isolation
    none, and each test file becomes an acceptance check.
  - a project deployed by docker compose: real isolation (a runner-owned project
    name and ports), a compose bringup, and health/acceptance left as TODOs for
    the user, because a machine cannot guess what "it works" means for a service.

Standard library only. The draft is a starting point, never the last word.
"""

import argparse
import glob
import json
import os
import sys


def _first(root, names):
    for n in names:
        if os.path.exists(os.path.join(root, n)):
            return n
    return None


def detect(repo):
    f = {}
    f["git"] = os.path.isdir(os.path.join(repo, ".git"))
    f["compose"] = _first(repo, ["docker-compose.yml", "compose.yaml",
                                  "bundle/docker-compose.yml"])
    f["makefile"] = _first(repo, ["Makefile"])
    f["python"] = bool(glob.glob(os.path.join(repo, "**", "*.py"), recursive=True))
    f["node"] = os.path.exists(os.path.join(repo, "package.json"))
    tests = sorted(glob.glob(os.path.join(repo, "tests", "test_*.py")) +
                   glob.glob(os.path.join(repo, "test_*.py")))
    f["pytest_files"] = [os.path.relpath(t, repo) for t in tests]
    f["make_test"] = bool(f["makefile"]) and "test:" in _read(os.path.join(repo, "Makefile"))
    return f


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def author(repo, app=None, clone=None):
    f = detect(repo)
    app = app or os.path.basename(os.path.abspath(repo))
    binds = [{"name": "git", "probe": "git --version", "required": True}]
    if f["python"]:
        binds.append({"name": "python3", "probe": "python3 --version", "required": True})

    if f["compose"]:
        binds += [
            {"name": "docker", "probe": "docker version", "required": True},
            {"name": "docker-compose", "probe": "docker compose version", "required": True},
        ]
        profile = {
            "isolation": {
                "namespace_env": "COMPOSE_PROJECT_NAME",
                "port_envs": ["_TODO_name_the_host_port_env_vars"],
                "collision_probe": "test -z \"$(docker ps -aq --filter label=com.docker.compose.project=$COMPOSE_PROJECT_NAME)\"",
                "teardown": f"docker compose -f {f['compose']} down -v",
            },
            "preflight": [
                {"name": "docker-daemon", "probe": "docker info >/dev/null 2>&1", "required": True},
            ],
            "bringup": [
                {"name": "compose-up",
                 "run": f"docker compose -f {f['compose']} up -d --build --wait --wait-timeout 600"},
            ],
            "health": [{"name": "_TODO", "check": "curl -fsS http://localhost:$_TODO/health"}],
            "acceptance": [{"name": "_TODO_name_a_check_that_passes", "check": "false"}],
        }
    else:
        acc = [{"name": os.path.splitext(os.path.basename(t))[0], "check": f"python3 {t}"}
               for t in f["pytest_files"]]
        if not acc and f["make_test"]:
            acc = [{"name": "make-test", "check": "make test"}]
        profile = {
            "isolation": {"none": True,
                          "why": "hermetic: runs the project's own tests in a throwaway clone; "
                                 "starts no daemons, binds no host ports, writes no shared state"},
            "bringup": [{"name": "no-build", "run": "true"}],
            "health": [{"name": "clone-present", "check": "test -e ."}],
            "acceptance": acc or [{"name": "_TODO_name_a_check_that_passes", "check": "false"}],
        }

    return {
        "app": app,
        "_authored_by": "hoist author (draft; refine the _TODO fields with the user)",
        "source": {"clone": clone or os.path.abspath(repo), "dir": app},
        "binds": binds,
        "default_profile": "default",
        "profiles": {"default": profile},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="draft a Layer 2 config for a repo")
    ap.add_argument("repo", help="path to the repo to make hoistable")
    ap.add_argument("--app", default=None)
    ap.add_argument("--clone", default=None, help="clone source to record (default: the repo path)")
    ap.add_argument("--out", default=None, help="write config here (default: stdout)")
    args = ap.parse_args(argv)
    config = author(args.repo, args.app, args.clone)
    text = json.dumps(config, indent=2)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"drafted config for {config['app']} -> {args.out}")
        todos = json.dumps(config["profiles"]).count("_TODO")
        if todos:
            print(f"  {todos} _TODO field(s) for the user to fill (the checks a machine cannot infer)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
