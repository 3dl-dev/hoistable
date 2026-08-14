# Handoff (successor session)

You are waking mid-process, not starting fresh. This is where the work stood at the
last pause. Re-derive current status by running things, do not trust this file as
frozen truth.

## Where the work lives

- Everything is on `main` now (merged from `worktree-impl-baseline`, which is still on
  disk under `.claude/worktrees/` and fully merged; safe to remove with
  `git worktree remove` if you want).
- A real GitHub pre-release exists: `operators v0.0.1` on `baron-3dl/hoistable`
  (private). A config pins it by URL + sha256; `hoist` pulls it via `gh`.

## Verify before trusting (do this first)

    python3 -m unittest discover -s tests -p "test_*.py"    # last run: 40 passed

These are **builder** checks — you invoking the neutral core to grade it. They are not
the product surface: agent-first, users invoke the hoist *skill*, never a `.py`.

End-to-end proofs, all re-runnable (see git history for the exact demo commands):
- `python3 hoist/hoist.py agent-dyno --target-dir <tmp>`  -> BUILT 2/2 (by name via index.json)
- hoist hoistable's own config (examples/hoistable/config.json) -> BUILT 6/6 (self-hosting)
- EAF minimal-5 (examples/eaf/config.json) needs docker; hoists BUILT 2/2 in an
  isolated namespace. WARNING: only run EAF hoist on a host that is NOT already running
  the `enterprise-ai` compose project, or in a sandbox (see the incident below).

## What is built

- `envelope/envelope.py` -- the neutral grader + enforced invariants (isolation,
  no-silent-success, blast-radius). The load-bearing safety code.
- `hoist/` -- the neutral core the **hoist skill** calls (the entry point is the skill,
  not these files): `hoist.py` (config discovery + pin resolution + the enforced pass),
  `pins.py` (fetch+verify+extract a pinned operator kit), `author.py` (draft a config;
  a reference helper, the real authoring is the agent's job).
- `operators/{develop,preflight,sysop,petard}/` -- SKILL.md method (skill-primary) plus,
  for petard and develop, tested reference code. petard: provision.sh + cards.py +
  translate.py (a local model translates ops intent to a grounded command, frontier-down).
- `release/build_release.py` -- package the operator kit for a GitHub release.
- `index.json` -- the discovery registry (`HOIST_INDEX` overrides it).

## Decisions that are settled (do not re-litigate)

- **Agents author, code enforces.** The flexible, per-environment work (authoring a
  config, understanding/forking/upstreaming a project) is the agent's, done with
  judgment. Code is the operator only where it is a guarantee (the invariants) or a
  no-frontier fallback (petard). Build-rule 1: checked-in code is a reference build.
- **Pinned-URL repeatability**, not vendoring (build-rule 4). Pins are URLs.
- The EAF stomp incident: a first hoist replayed EAF's own compose (fixed project name +
  ports) and recreated a live `enterprise-ai` stack. Fixed structurally (isolation
  refusal + blast-radius check). The live stack was restored; no data lost.

## Next execution pointers (open work)

1. **Environmental sandbox** (priority). The isolation invariants are bounded: they
   guard only the runner path and check a declaration, not behavior. The real guarantee
   is running a hoist inside a throwaway container/VM where stomping is physically
   impossible. This is also the still-open "literal fresh-VM EAF grade" from
   `hoistable-bc4`.
2. Web-search discovery (the last `resolve_config` fallback in `hoist/hoist.py`).
3. Host `index.json` at a URL so `hoist <name>` works without the repo.
4. The `gh pr create` step for develop's contribute-back (documented, not automated).

## Trail

rd item `hoistable-270` carries the full evolution; `hoistable-bc4` is the EAF slice.
Git history on `main` is the commit-by-commit record.
