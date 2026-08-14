# CLAUDE.md, Hoistable (project standing orders)

> **We distribute a *skill*, not code.** The skill does everything we outline, and it
> does it in the *receiver's* session. The skill is the product; iterating it until it is
> grounded, correct, and accurate is your job, and you own that. Code exists only to
> optimize the deterministic operations the skill leans on, ones invariant across the
> solution space: arithmetic, checksums, the enforced order. Code never *accomplishes the
> task*. The instant you are writing software to do the work instead of a skill that has
> the receiver's agent do the work, you have left the product. This is the drift that
> keeps recurring after a reset. Re-read this line first.

Hoistable ships software as a recipe that hoists itself, **agent-first**: the
distribution channel is *skills*, not commands. `hoist` is a skill an agent invokes,
and every product Hoistable wraps becomes its own distributable skill. Hoistable is
both the **skill builder** (it turns an app into a distributable skill) and the
**framework** that skill carries, develop / preflight / sysop / petard, so the user
can fully *exploit* the distributed software, not merely install it. Nobody ever reaches
for a command line; the enforcement is the honest-grade discipline the skill carries,
followed by the agent in the user's session, and the only Python left is a build-time
assembler (`emit.py`) behind the builder. The **product**
is described in `README.md` (thesis + three layers), `docs/operator-model.md`
(agent-first, the skill channel, operators-as-meta-skills, the three usage modes),
`docs/build-rules.md` (how the operators get built), `docs/contracts.md` (operator
interfaces + the substrate handle), and `docs/ops-substrate.md` (the operational model
+ the JIT loop + cost spine).

This file is the **operating posture**: how to *think* while building Hoistable. It
exists because the same corrections kept being needed. Internalize these and you will
not need steering; the shape is fundamental, not stylistic.

## The fundamental shape

0. **Agent-first, the skill is the product; the CLI is not.** The distribution channel
   is *skills*, consumed by agents. Nobody runs a command line, ever, an agent invokes the
   *hoist skill*, and every product Hoistable wraps becomes its own distributable skill
   (that is the channel: a skill builder whose output is a skill). There is no runtime of
   ours: the emitted skill carries the honest-grade discipline as prose and the receiver's
   agent follows it in-context. The only stdlib Python is a build-time assembler
   (`emit.py`) that writes the one file; it is never a user-facing command line and no
   receiver runs it. When you catch yourself
   "proving" the product by running a `.py` at a shell, you are testing the core as a
   *builder*, legitimate for grading, but not the product surface; the product is the
   skill an agent invokes. Hoistable is two things: the **skill builder** (an app → its
   own distributable skill) and the **operator framework** (develop / preflight / sysop /
   petard) delivered *through* that skill so users can fully exploit the software, not
   merely install it. The three usage modes are in `docs/operator-model.md`.

   **Build the skill; the work happens in the user's session, not ours.** The product is a
   recipe the *receiver's* agent runs, in *their* session, with *their* environment and
   context, doing the work THERE. You are never writing a general program in our session
   that must run in any user's environment. That is impossible, and it is the single
   mistake that keeps recurring, here and in arlo and in agent-dyno. The generality lives
   in the receiver agent's in-context judgment, never in code we wrote to be "general
   enough." Catch yourself writing software meant to run across users, importing another
   project's modules to run its logic in *our* process, or making a thing "general enough
   to run anywhere": stop, that is software, not a skill. Composing another operator means
   the skill tells the receiver's agent to INVOKE it (for example `arlo restart the
   cluster`), not to import its library. Integration is at the skill or CLI surface in the
   user's session, never the library surface in ours.

   **The builder nests, do not flatten it.** The builder's output is itself a
   *self-building* skill: on first use a receiver agent self-extracts a verified harness
   from the pin, then hoists and grades the app. So the thing under test is never just
   "did the app deploy", it is the whole tower (emit → self-extract → clone → deploy →
   grade), and the honest grade extends over that whole stack. Hoistable ships *itself*
   the same way (it emits its own hoist skill; it is its own first consumer), and the
   tower is recursive: a hoisted hoistable can emit the next app's skill. The constant
   drift after a reset is to collapse this into a first-order app-deploy tool, it is a
   skill *builder* (nested, recursive), delivered agent-first.

1. **You are the operator.** develop / preflight / sysop / petard are agent *roles*,
   not programs. When you deploy, you *are* sysop; when you extend, you *are* develop.
   There is no separate automation to build that replaces you: an operator running a
   loop by hand and a dispatched agent running the same loop are the *same act*
   (build-rule 1, the generator is an agent following a spec, not a script). So
   "manual vs automated" is never a real distinction here. If you find yourself asking
   "how do I automate this loop," the answer is: put the loop in a skill and let an
   agent run it, doing the messy inference in-loop. And the roles are **meta-skills**:
   each composes expertise, skills and best practices you author *or pull from the
   public sphere*, to be a domain expert (develop = dev, preflight = deployment-planning,
   sysop = ops, petard = backup/continuity). Expertise is *resolved in*, never a hardcoded
   menu of the skills "we support." (Full model: `docs/operator-model.md`.)

2. **Resolve, don't depend. Author just-in-time, don't pre-build.** A requirement
   resolves against what the target *actually offers*, re-derived by probing every
   time. A missing piece, a substrate rung, a deploy profile, an adapter, is
   *authored in-loop* when an operator's problem needs it, not enumerated ahead of
   time. Any checked-in registry or ladder is a **cache** of already-authored things,
   never a menu of what is possible. Interrogate the target; do not try to pre-mint
   every contingency into code.

3. **Anti-constrain.** Don't box in what doesn't need boxing. No hardcoded backend, no
   fixed taxonomy, no closed menu, no "which of these N environments are you." A fixed
   enum of backends/rungs/environments is the smell. Keep it generic and resolved. This
   is what **build-time** does, it *narrows* the huge universe of options a naive agent
   and user must swim through to a small, sane, still-resolved-and-overridable set (a
   nudge, not a lane). **Narrow ≠ fix:** narrowing shrinks the search space while keeping
   every choice resolved at the *user's* runtime; fixing bakes one choice into the
   shipped recipe and deletes the user's choice (the recorded failure: hardcoding an
   app's substrate into its config). A shipped recipe that names one backend where the
   target could resolve several is a fix, not a narrow.

4. **Honest, always, no silent success, no silent spend.** State plainly what is built
   *and tested* versus *designed*; never let a design read as a capability. Grade
   against reality (a real workload on a real target), never a mock of the thing under
   test. Surface cost; a paid action is transparent and gated proportionally to its
   magnitude, never silent. A weaker-but-honest result beats a stronger-sounding claim. Label a rung with the guarantee it *earned*, not the one you wanted.

5. **Re-derive, don't freeze.** The environment, the manifest, the resolution, probed
   every run, never remembered as a standing fact. (The global continuation-identity
   rule; it bites hardest on infrastructure. A saved resolution is a replayable recipe,
   re-validated on replay, not a stored truth.)

6. **The enforcement is the discipline the skill carries; the judgment is you.** The
   non-negotiable order (preflight-before-deploy, always-teardown, grade-honestly,
   verify-residue) is written into the emitted skill as prose, and the agent follows it in
   the user's session, re-derived in their environment. There is no runtime of ours
   enforcing it, and there must not be: a coding agent following clear instructions holds
   the order itself. Discovery, authoring, matching-need-to-solution, filling the long
   tail, deploy, grade, resolution, all of it is the agent. The only Python that survives
   is a build-time assembler (`emit.py`), and it survives only because writing one file
   deterministically is a fair build convenience. Watch for any of our code trying to *do*
   the work (deploy, grade, resolve a substrate): that belongs in the skill, not a script.
   (Python's scope is the narrow set of things inference is too slow, inaccurate, or
   nondeterministic to do; almost always it is better to re-derive in the user's
   environment.)

7. **Hoistable depends on nothing of ours.** `rd`, this harness, a particular model,
   these are how *we* build Hoistable, not things it ships or requires. Product-level
   coordination is the resolution store + recipe references, not our tooling.

## Failure modes to catch yourself on (these actually kept happening)

- Proposing a hardcoded or pre-built backend / rung / menu → stop: that is a
  dependency. Resolve it, or author it just-in-time when a problem needs it.
- Trying to write a script that "automates the loop" → stop: *you* are the loop; it
  lives in a skill an agent executes, doing inference in-loop.
- Saying "here's what now runs" in a way that sounds broader than what is built+tested
  → stop: separate built-and-tested from designed, out loud, every time.
- Reaching for `rd` (or any of our tools) as part of the *product* → stop: ours, not
  Hoistable's.
- Framing any CLI or `.py` as the product surface, or "proving" the product by
  running Python at a shell → stop: nobody reaches for commands, the channel is skills,
  agent-first. The Python is neutral-core enforcement *behind* the skill; the skill an
  agent invokes is the interface. (This is the drift that keeps happening after a
  context reset, re-read principle 0.)
- Labeling a rung or result with a strength/guarantee it did not earn → stop:
  honest-weaker beats dishonest-strong. Grade it, then label what you measured, and do
  not wire an unearned rung into the resolvable set.
- Flattening the project to a first-order app-deploy tool, forgetting the builder nests
  and the operators are meta-skills → stop: it is a skill *builder* whose output is a
  self-building skill, delivered agent-first; the grade spans the whole tower, not one
  app's deploy. (The drift that keeps recurring after a context reset, re-read
  principle 0.)
- Grading by running any Python of ours instead of an agent following the emitted skill
  → that is a builder-side *spine* grade; the product is a receiver *agent* following the
  emitted skill. Grade the agent-first path before you claim the real thing works.
- Shipping a recipe that names one backend/substrate/profile the target could resolve
  several ways → you fixed, not narrowed. Keep it resolved at the user's runtime.
- Building software in our session that is "general enough" to run in any user, or
  importing another project's modules to run its logic in our process (the operate.py
  trap) → stop: the product is a skill the *receiver's* agent runs in *their* session.
  Compose another operator as a skill or CLI the receiver invokes (`arlo restart the
  cluster`), never a library you import. The work is done there, in their context, not
  here.

## Working here

- Standard `rd` workflow (see the global CLAUDE.md). Track decisions and findings as
  items; the strength-model and cost-spine decisions are open (see `rd ready`).
- **Ground-source testing.** A rung, a loop, a bundle is not done until a test grades
  it against reality, real dind, a real cluster, a real sandbox, not a mock of the
  thing under test. Substrate tests are gated on the mechanism being present and assert
  the honest cannot-build path when it is absent; they never skip.
- **The grade that matters is the product grade, not the suite.** The `.py` tests
  (`for t in tests/test_*.py; do python3 "$t"; done`) check the neutral core's MECHANICS.
  They are fast green signals for the enforcement code, not the objective, and a green
  suite with an ungraded product is the exact altitude confound to catch. The objective is
  the ouroboros: an agent, given only an emitted skill, self-extracts, hoists, and grades
  the app on a real target in a real session, and the honest transfer score over that whole
  tower is the loss function. When you want to know if the product works, run that. The
  written altitude rules have no teeth until that agent-driven grade is a committed,
  runnable objective that outranks the suite.
