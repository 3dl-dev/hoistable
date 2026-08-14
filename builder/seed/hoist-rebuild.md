# This skill hoists <app> before it reports <app> is up

You are about to bring up **<app>** from a *recipe*, not from a finished instance. The
skill ships <app> as source: a carried recipe plus the pin to its harness, like a
self-extracting archive that carries both its contents and the unpacker. Before you tell
anyone <app> is running, HOIST it against **this** target and GRADE it honestly. This is
agent-first — you do the work in-loop; nobody runs a command line. The material is the
carried recipe, the binds, the checks, and the acceptance in the sections below.

Two roles run through this. The **author** wrapped <app> as this skill on their machine.
The **receiver** is whoever installs it — a different target, whose substrate, secrets,
and paths you resolve here. You work so the receiver reaches a real, graded <app> — or an
honest reason it could not, never a silent success.

## Hoist recipe (run before your first report that <app> is up)

1. **Cache / idempotency.** If <app> is already hoisted on this target in this session (a
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
   teardown. You never re-run <app>'s own singular deployment onto a live host.

5. **Grade.** The acceptance checks rebuild on THIS target. Compute the honest transfer
   score — how many of the acceptance checks passed, N of M — and name every check that did
   not transfer. Because acceptance runs against the real target, this score is honest, not
   a memory of the author's run.

6. **Report** the outcome in one line, using one of the templates below. Never let a design
   read as a running system; if it did not transfer, say what did not.

7. **Hand off.** Hand the user to the operators the carried recipe includes (develop,
   sysop, petard) so they can *exploit* <app> — extend it, operate it, keep it running
   lights-out — not merely have it installed.

Before your first report, state in one line what happened, only one line, and do not
narrate the loop, using one of these templates:
- "Built <app>. Acceptance transferred N of M on this target. Ready."
- "Built <app>, but N of M acceptance checks did not transfer here: [the specific checks]."
- "Cannot build <app>: this target is missing [the named bind or substrate strength]."
- "Reusing the <app> hoist from earlier this session. Ready."

The failure to avoid: reporting <app> is up because the recipe *looks* right. It is up only
when it deployed and its acceptance transferred on this target. Grade it, then report what
you measured.
