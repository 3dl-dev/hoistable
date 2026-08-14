---
name: hoist-hoistable
description: Hoist hoistable onto your target — on first use, self-extract the hoistable harness and clone, configure, deploy, and grade hoistable, reporting an honest transfer score. Agent-first; no commands.
---

# This skill hoists hoistable before it reports hoistable is up

You are about to bring up **hoistable** from a *recipe*, not from a finished instance. The
skill ships hoistable as source: a carried recipe plus the pin to its harness, like a
self-extracting archive that carries both its contents and the unpacker. Before you tell
anyone hoistable is running, HOIST it against **this** target and GRADE it honestly. This is
agent-first — you do the work in-loop; nobody runs a command line. The material is the
carried recipe, the binds, the checks, and the acceptance in the sections below.

Two roles run through this. The **author** wrapped hoistable as this skill on their machine.
The **receiver** is whoever installs it — a different target, whose substrate, secrets,
and paths you resolve here. You work so the receiver reaches a real, graded hoistable — or an
honest reason it could not, never a silent success.

## Hoist recipe (run before your first report that hoistable is up)

1. **Cache / idempotency.** If hoistable is already hoisted on this target in this session (a
   prior graded namespace exists, or a resolution is recorded here), reuse it, emit the
   Reusing line, and skip to step 6. Do not re-deploy over a live instance.

2. **Resolve the binds.** For each entry in the binds section, probe this target for the
   matching capability, and resolve the isolation substrate to the required strength the
   carried recipe names. If a *required* bind has no match here, or no substrate meets the
   required strength, STOP, deploy nothing, and report cannot-build naming the missing one.
   Never guess and never substitute. If you cannot positively confirm a required bind,
   treat it as missing.

3. **Self-extract the harness (the bootstrap).** The carried recipe carries an
   `operators` pin (`version`, `url`, `sha256`) — but the harness that runs the hoist
   lives *inside* that kit, so you unpack it yourself first, and only after verifying it.
   There is no `pins.py` to call yet; getting it is this step. Do exactly this:
   (a) fetch the tarball at the pin `url`; (b) compute its sha256 and confirm it equals
   the pin's `sha256` — if it does not, STOP, report cannot-build (tampered or wrong kit),
   and never unpack or run an unverified tarball; (c) extract the verified tarball — that
   unpack IS the self-extraction, and it yields the harness: `hoist/{hoist.py,pins.py}`,
   `envelope/{envelope.py,substrate.py}`, and the develop/preflight/sysop/petard
   operators. From here the extracted kit drives: its `hoist.py` runs the graded pass and
   its `pins.py` re-verifies the kit into the version cache. Because you checked the
   tarball's sha256 by hand before unpacking, nothing unverified ever executes.

4. **Know early, then deploy.** Run preflight first — it deploys nothing. If it says
   cannot-build, stop at the door and give the user the named reason. Otherwise run the
   full graded pass through the neutral-core grader (`envelope`), which *enforces* the
   invariants: a runner-owned isolated namespace (non-destructive onboarding), and
   teardown. You never re-run hoistable's own singular deployment onto a live host.

5. **Grade.** The acceptance checks rebuild on THIS target. Compute the honest transfer
   score — how many of the acceptance checks passed, N of M — and name every check that did
   not transfer. Because acceptance runs against the real target, this score is honest, not
   a memory of the author's run.

6. **Report** the outcome in one line, using one of the templates below. Never let a design
   read as a running system; if it did not transfer, say what did not.

7. **Hand off.** Hand the user to the operators the carried recipe includes (develop,
   sysop, petard) so they can *exploit* hoistable — extend it, operate it, keep it running
   lights-out — not merely have it installed.

Before your first report, state in one line what happened, only one line, and do not
narrate the loop, using one of these templates:
- "Built hoistable. Acceptance transferred N of M on this target. Ready."
- "Built hoistable, but N of M acceptance checks did not transfer here: [the specific checks]."
- "Cannot build hoistable: this target is missing [the named bind or substrate strength]."
- "Reusing the hoistable hoist from earlier this session. Ready."

The failure to avoid: reporting hoistable is up because the recipe *looks* right. It is up only
when it deployed and its acceptance transferred on this target. Grade it, then report what
you measured.

## The carried recipe (the authority; the operators pin travels with it)

```json
{
  "_authored_by": "hoist author (self-hosting reference: hoistable's own Layer 2 config)",
  "app": "hoistable",
  "binds": [
    {
      "name": "git",
      "probe": "git --version",
      "required": true
    },
    {
      "name": "python3",
      "probe": "python3 --version",
      "required": true
    }
  ],
  "default_profile": "default",
  "operators": {
    "sha256": "b90443e62cd83a05bc733fa32927bc7f62092ca099aeb579d47780a376309dbf",
    "url": "https://github.com/3dl-dev/hoistable/releases/download/operators-v0.4.0/hoistable-operators-0.4.0.tgz",
    "version": "0.4.0"
  },
  "profiles": {
    "default": {
      "acceptance": [
        {
          "check": "python3 tests/test_author.py",
          "name": "test_author"
        },
        {
          "check": "python3 tests/test_cards.py",
          "name": "test_cards"
        },
        {
          "check": "python3 tests/test_envelope.py",
          "name": "test_envelope"
        },
        {
          "check": "python3 tests/test_hoist.py",
          "name": "test_hoist"
        },
        {
          "check": "python3 tests/test_petard.py",
          "name": "test_petard"
        },
        {
          "check": "python3 tests/test_translate.py",
          "name": "test_translate"
        }
      ],
      "bringup": [
        {
          "name": "no-build",
          "run": "true"
        }
      ],
      "health": [
        {
          "check": "test -e .",
          "name": "clone-present"
        }
      ],
      "isolation": {
        "none": true,
        "why": "hermetic: runs the project's own tests in a throwaway clone; starts no daemons, binds no host ports, writes no shared state"
      }
    }
  },
  "source": {
    "clone": "https://github.com/3dl-dev/hoistable.git",
    "dir": "hoistable"
  }
}
```

## Binds (resolve these on the target; a missing required one is cannot-build)

- `git` (required) — probe: `git --version`
- `python3` (required) — probe: `python3 --version`
- isolation substrate: none required — this profile is hermetic (hermetic: runs the project's own tests in a throwaway clone; starts no daemons, binds no host ports, writes no shared state).

## Checks (invariants every hoist obeys)

- **Non-destructive onboarding.** The hoist lands in a runner-owned isolated namespace (its own name, ports, storage); a deploying profile that declares no isolation is refused; teardown always runs. You never re-run hoistable's own singular deployment onto a live host.
- **No silent success.** hoistable is graded on the real target; a hoist that cannot say it worked says what did not transfer. A design never reads as a running system.
- **Verified harness.** The operator kit is run only after its sha256 matches the carried pin; a tampered or unreachable kit is cannot-build, named.

## Acceptance (the held-back transfer test; the honest score)

- `test_author`: `python3 tests/test_author.py`
- `test_cards`: `python3 tests/test_cards.py`
- `test_envelope`: `python3 tests/test_envelope.py`
- `test_hoist`: `python3 tests/test_hoist.py`
- `test_petard`: `python3 tests/test_petard.py`
- `test_translate`: `python3 tests/test_translate.py`
