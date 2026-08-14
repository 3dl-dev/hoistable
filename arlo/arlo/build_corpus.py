#!/usr/bin/env python3
"""arlo: the no-frontier operational fallback. Corpus builder + grounded answerer.

arlo is the operator that keeps you able to act when the frontier stack is down
or rate limited. It is not autonomous ops and not a smart model; its strength is a
fresh corpus of ground truth plus retrieval, run on an independent path.

This enforces the arlo grounding invariant, in code:

  - Generated, not authored. The corpus is built ONLY by running commands and
    capturing their output: --help dumps, schema introspection, runbook harvests.
    There is no argument that puts hand-written text into the corpus, so it cannot
    drift from ground truth the way a maintained doc does.

  - Retrieval grounded, not generative. Answering returns lines pulled from the
    corpus, each tagged with the command that produced it. It never synthesizes a
    command shape from parametric memory. Every line it hands back is a substring
    of the corpus it was built from.

Standard library only. A weak local model (or a human) reads the grounded answer;
what makes arlo correct is the freshness of the corpus, not the reader.
"""

import argparse
import json
import subprocess
import sys


def _host_run(cmd, timeout):
    """Run a command on the host and return (rc, text). The default harvester."""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"(timed out after {timeout}s)"
    except Exception as e:  # noqa: BLE001
        return 127, f"(could not run: {e})"


def environment_runner(exec_in_env, cwd, env=None):
    """Adapt an arbitrary "run a command in some environment" handle to the
    (cmd, timeout) -> (rc, text) shape arlo's harvesters expect. The host runner
    above harvests from the host; pass this instead to harvest ground truth from
    INSIDE wherever the system actually runs (a container, a VM, a cluster, a remote
    box), with no host access. `exec_in_env` is any callable
    (cmd, cwd, env, timeout) -> (rc, text). arlo names nothing about your
    environment; you inject how to reach it."""
    return lambda cmd, timeout=60: exec_in_env(cmd, cwd, env or {}, timeout)


def build_corpus(sources, timeout=60, run=None):
    """sources: list of {name, cmd}. Runs each cmd and captures its output as a
    corpus entry whose provenance IS the command. Hand-written text is never
    accepted: the only way in is to run something and harvest what it says.

    run is the command runner, (cmd, timeout) -> (rc, text). It defaults to the
    host (_host_run); pass environment_runner(exec_in_env, cwd) to harvest from
    inside wherever the system runs so the corpus reflects what is actually live,
    not the host."""
    run = run or _host_run
    corpus = []
    for s in sources:
        rc, text = run(s["cmd"], timeout)
        corpus.append({
            "name": s["name"],
            "source_cmd": s["cmd"],   # provenance: how this entry was generated
            "text": text,
            "rc": rc,
        })
    return corpus


def answer(corpus, query, top=10):
    """Retrieval-grounded lookup: return the corpus lines that match the query,
    ranked by how many query terms they contain (most first), each with the
    source command it came from. No generation: every returned line is a line
    that is present in the corpus. A line matching no term is never returned, and
    when nothing matches the result is empty (arlo does not guess)."""
    terms = [t.lower() for t in query.split() if t]
    if not terms:
        return []
    hits = []
    for entry in corpus:
        for line in entry["text"].splitlines():
            s = line.strip()
            if not s:
                continue
            score = sum(1 for t in terms if t in s.lower())
            if score:
                hits.append({"line": s, "from": entry["source_cmd"], "score": score})
    hits.sort(key=lambda h: -h["score"])
    return hits[:top]


def main(argv=None):
    ap = argparse.ArgumentParser(description="arlo corpus builder / grounded answerer")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build a corpus from a sources JSON")
    b.add_argument("sources", help="JSON: [{name, cmd}, ...]")
    b.add_argument("--out", required=True)
    a = sub.add_parser("ask", help="retrieval-grounded lookup against a corpus")
    a.add_argument("corpus", help="a corpus JSON produced by build")
    a.add_argument("query", nargs="+")
    args = ap.parse_args(argv)

    if args.cmd == "build":
        with open(args.sources) as f:
            sources = json.load(f)
        corpus = build_corpus(sources)
        with open(args.out, "w") as f:
            json.dump(corpus, f, indent=2)
        print(f"built corpus of {len(corpus)} entries from {len(sources)} sources -> {args.out}")
        return 0
    with open(args.corpus) as f:
        corpus = json.load(f)
    hits = answer(corpus, " ".join(args.query))
    if not hits:
        print("no grounded match. arlo does not guess.")
        return 1
    for h in hits:
        print(f"[{h['score']}] {h['line']}\n      (from: {h['from']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
