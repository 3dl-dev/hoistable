# This skill sets <app> up before it reports <app> is up

You are about to bring **<app>** up from a *recipe*, not from a finished instance. This
skill carries <app> as source: the recipe below (its binds, isolation, bringup, health,
and acceptance) is everything you need. You do the work **here, in this session, on this
target**, with ordinary tools you already have (git, the container runtime, a shell). You
fetch and run no toolchain and no program of anyone else's: the discipline below is yours
to follow, in context. Nobody runs a command line; you are the one who hoists <app>.

Two roles run through this. The **author** packaged <app> as this skill on their machine.
The **receiver** is you, on a different target, whose substrate, secrets, and paths you
resolve here. Work so the receiver reaches a real, graded <app>, or an honest reason it
could not, never a silent success.

Before you tell anyone <app> is up, <verb> it against **this** target and GRADE it
honestly. The carried recipe below is the authority; the steps here are how you run it.

## The honest-grade discipline (run in this order; the order is the guarantee)

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

4. **Preflight (know early; deploy nothing).** Clone the source (into the sandbox if you
   stood one up), then run the recipe's preflight probes. A required preflight blocker is
   **cannot-build**: name it and stop at the door, before anything deploys.

5. **Deploy (the install gate).** Run the recipe's bringup steps, inside the isolated
   namespace or sandbox, with the free ports and namespace set. This is the only place
   <app> is stood up, and only here, never onto a live host.

6. **Health, then acceptance (the honest transfer score).** Run the recipe's health checks
   and count how many of M pass. Only if the install gate is fully up, run the recipe's
   held-back **acceptance** checks. Their pass fraction, N of M, is the honest transfer
   score: whether <app> really *works* here, not merely that it came up. Name every check
   that did not transfer.

7. **Always tear down, then verify no residue.** Run the recipe's teardown; if you stood
   up an environmental sandbox, destroy it. Then confirm your footprint left nothing behind
   on the host: the sandbox's resources are gone, the host-floor namespace is reclaimed. A
   deploy that changed state outside its namespace is a blast-radius violation; report it.

8. **Report one honest line** (templates below). Never let a design read as a running
   system; if something did not transfer, say what.

9. **Hand off.** Point the user at how to use, operate, or keep <app> running (per the
   recipe's follow-ups), so they can *exploit* <app>, not merely have it installed.

The outcome is exactly one of:
- **built**, the install gate came up AND every acceptance check passed.
- **honest-failure**, it came up but something did not transfer; say what.
- **cannot-build**, a required bind, a preflight blocker, or the isolation strength is
  missing; name it.

State it in one line, only one, and do not narrate the loop:
- "Built <app>. Acceptance transferred N of M on this target. Ready."
- "Built <app>, but N of M acceptance checks did not transfer here: [the specific checks]."
- "Cannot build <app>: this target is missing [the named bind or isolation strength]."
- "Reusing the <app> setup from earlier this session. Ready."

The failure to avoid: reporting <app> is up because the recipe *looks* right. It is up only
when it deployed and its acceptance transferred on THIS target. Grade it, then report what
you measured.
