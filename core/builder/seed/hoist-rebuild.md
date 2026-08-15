# This skill sets <app> up before it reports <app> is up

You are about to bring **<app>** up from a *recipe*, not from a finished instance. This
skill carries <app> as source: the recipe below (its binds, isolation, bringup, health,
and acceptance) is everything you need. You do the work **here, in this session, on this
target**, with ordinary tools you already have (git, the container runtime, a shell). You
fetch and run no toolchain and no program of anyone else's: the discipline below is yours
to follow, in context. Nobody runs a command line; you are the one who hoists <app>.

The **objective is a running, usable <app>** the user can exploit, not a test that proves
it then throws it away. You grade as you go so you never lie about whether it is really up,
but on success you **leave <app> running** and hand the user off to the operators, not an
empty target.

Two roles run through this. The **author** packaged <app> as this skill on their machine.
The **receiver** is you, on a different target, whose substrate, secrets, and paths you
resolve here. Work so the receiver reaches a real, running, graded <app>, or an honest
reason it could not, never a silent success and never a teardown of the thing they asked
for.

Before you tell anyone <app> is up, <verb> it against **this** target and GRADE it
honestly. The carried recipe below is the authority; the steps here are how you run it.

## The hoist discipline (run in this order; the order is the guarantee)

1. **Reuse if already up.** If <app> is already up on this target in this session, reuse
   it, say so, and skip to the report. Never redeploy over a live instance.

2. **Binds gate (can this host even do the hoist).** For each bind in the recipe, run its
   probe on the host. A missing *required* bind is **cannot-build**: name it and stop,
   deploying nothing. Do not guess and do not substitute; if you cannot positively confirm
   a required bind, treat it as missing.

3. **Resolve the isolation (a deploy must never touch host state).** A profile that
   deploys MUST be isolated. Resolve this against the target, do not assume it:
   - If the recipe requires an **environmental** substrate (a sandbox a deploy cannot
     escape, docker-in-docker for example), stand up the strongest one the target offers
     and run every following step *inside* it; the sandbox is the isolation boundary. If
     the target offers nothing that meets the required strength, stop: **cannot-build**,
     name the strength that was missing.
   - Otherwise use the recipe's own **namespace** on the host floor: a fixed project name,
     OS-chosen free ports (never a hardcoded port that could already be taken), named
     volumes, so the deploy cannot collide with or reach anything else. If the recipe
     gives a collision probe, run it first; a dirty namespace is cannot-build.
   - A deploying profile that declares no isolation at all is refused. Do not run it.
   This isolation is <app>'s **home**, not a scratch space: the running app lives here.

4. **Preflight (know early; deploy nothing).** Clone the source (into the sandbox if you
   stood one up), then run the recipe's preflight probes. A required preflight blocker is
   **cannot-build**: name it and stop at the door, before anything deploys.

5. **Deploy (the install gate).** Run the recipe's bringup steps, inside the isolated
   namespace or sandbox, with the free ports and namespace set. This is where <app> is
   stood up, and only here, never onto a live host.

6. **Health, then acceptance (the honest transfer score).** Run the recipe's health checks
   and count how many of M pass. Only if the install gate is fully up, run the recipe's
   held-back **acceptance** checks against the running instance. Their pass fraction, N of
   M, is the honest transfer score: whether <app> really *works* here, not merely that it
   came up. Name every check that did not transfer.

7. **Land it, or clean up honestly.** This step is the fork the objective turns on:
   - **On success (built): leave <app> running.** It is up in its own isolation, reachable,
     and that is the deliverable, not residue. Do **not** tear it down; the user asked for a
     running app. Note where it is reachable (the URL, port, or namespace) for the report.
   - **On failure (honest-failure or cannot-build): tear the broken instance down** so the
     host is left as you found it, and say what failed.
   - **If you were asked only to PROVE it would work** (a feasibility or transfer check, not
     "run it for me"): deploy into a throwaway, grade, then tear it down leaving no residue.
   In every case you leave nothing **outside** <app>'s own isolation; the host stays clean.

8. **Report one honest line** (templates below). Never let a design read as a running
   system; if something did not transfer, say what.

9. **Hand off.** Point the user at the operators the recipe carries, develop, sysop,
   petard, and at how <app> is reached and kept running, so they can *exploit* <app>, not
   merely have had it installed.

The outcome is exactly one of:
- **built**, the install gate came up AND every acceptance check passed; <app> is left
  running.
- **honest-failure**, it came up but something did not transfer; say what, and tear the
  partial instance down.
- **cannot-build**, a required bind, a preflight blocker, or the isolation strength is
  missing; name it, having deployed nothing.

State it in one line, only one, and do not narrate the loop:
- "Built <app>. Acceptance transferred N of M on this target. Running at [where]; hand off
  to sysop to keep it up."
- "Built <app>, but N of M acceptance checks did not transfer here: [the specific checks]."
- "Cannot build <app>: this target is missing [the named bind or isolation strength]."
- "Reusing the <app> setup from earlier this session. Running at [where]."

The failure to avoid: reporting <app> is up because the recipe *looks* right, or tearing
down the app the user asked to run. It is up only when it deployed and its acceptance
transferred on THIS target, and the user is up only when it is still running for them.
Grade it, leave it running, and report what you measured.
