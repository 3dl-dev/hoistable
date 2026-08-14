# Hoistable

Software that ships itself.

Software has been shipped as a prebuilt artifact: build once, distribute the
binary, and eat the long tail of per-environment gaps (config drift, platform
quirks, "works on my machine") as recurring cost. Hoistable inverts that. The unit
of distribution is a **skill that hoists the instance into place per install**: it
clones the repo, runs the configuration, does the deployment, and fills the Pareto
long-tail gaps that used to make distribution expensive. You ship the recipe, and
the software pulls itself up by its own bootstraps.

This is **agent-first**. The channel is skills, consumed by agents — an agent invokes
the skill, so no one is left reaching for a command line. Every product Hoistable wraps
becomes its own distributable skill, and Hoistable is both the **skill builder** that
produces it and the operator **framework** (develop / preflight / sysop / petard) that
skill carries, so users can fully *exploit* the software, not merely install it.

## hoist: the skill you invoke

`hoist` is a **skill an agent invokes** — the mental model is Homebrew, but agent-first,
never a command you type. You point it at an app and it takes you to a running, graded
system. It works in two modes:

- **The app is already distributed hoistably.** hoist finds its config the way `brew`
  finds a formula — through an index, a GitHub URL, or a web search — and runs it. This
  is `brew install`.
- **The app is not distributed hoistably.** hoist builds the config *with* you and makes
  *you* the author of that app's Layer 2. This is writing the formula, done with you
  instead of by you.

Either path ends at a deployed, operable system. That covers both audiences at once:
developers who want a way to distribute their software (as a skill), and users who want
to run software no developer ever distributed hoistably. Nobody reaches for a command
line; an agent runs the skill.

## The three layers

- **Layer 0, this repo.** The generators, plus a **versioned release** of the four
  operator skills (develop, preflight, sysop, petard). It also carries the index
  that `hoist` searches first.
- **Layer 1, the hoister skill (`hoist`).** You add it to your harness. Run it
  against an app to install or author it; run it inside a project to emit that
  project's distributable config. This is the `hoist` role doing its work.
- **Layer 2, the distributable config (the app's formula).** What an end user
  installs. On install it **drives**: it pins the operator-skill versions from the
  Layer 0 release (repeatability), does the local setup, clones the distributing
  project, asks the user what they are here to do (develop or deploy), and walks them
  through every prerequisite before it hands off to the operators. It takes the
  wheel; it never leaves the user at a blank prompt with nothing to do. It also carries
  the app's acceptance test and self-grades on the target (see below), so an install
  never reports success it did not earn.

## The operators

Reusable, harness-agnostic, product-independent. Each is a skill that loads its
method into the session (and may dispatch agents for long-horizon work). A project's
config includes only the operators that project needs.

- **develop** (extend the product): add features through the product's manifest and
  handlers. Needed by extensible products; skipped by fixed tools.
- **preflight** (scope the deployment with the user): work with the user to fix the
  dimensions of the deployment, scale, single- vs multi-tenant, dev vs prod, and the
  infra target. It also probes the target for the known long-tail gaps and predicts
  whether the deployment will work, so the user learns early rather than mid-deploy.
  It emits a scoped deployment plan and a feasibility verdict, and hands both to sysop.
- **sysop** (deploy and operate): take the plan and chase it down. Deploy it, operate
  it day to day, and own the secrets, dovetailing with whatever the user already has
  or providing its own. sysop **composes external skills** for everything
  infra-specific (AWS, Azure, DigitalOcean, local VM, SSL and certs, SSO, security
  monitoring) instead of internalizing that knowledge.
  It deploys into an isolated namespace the runner owns (its own name, ports, and
  storage), never the app's own singular deployment, per the non-destructive
  onboarding invariant below. Product-specific run-time
  operations are sysop scope too: agent-dyno distributing its anonymized,
  technique-only leaderboard is sysop work inside that product, not a separate
  operator. (Note: agent-dyno's constitution forbids ranking or comparing
  individuals, so "publish each member's findings" is not a feature to lift from it;
  a per-member distribution would be a deliberate departure, decided upstream.)
- **petard** (lights-out fallback): the no-frontier operational fallback that sysop
  trains and keeps fresh. It is retrieval-grounded and runs independent of the
  frontier stack, on its own power and network path. Hoist with your own petard: the
  petard is the charge that lifts you when the frontier is down or rate limited. If
  it depends on the thing that is down, it is not a petard.

## The contracts

What keeps the operators reusable instead of re-smuggling product knowledge into
each config. The operators form a chain, develop to preflight to sysop to petard, and
there is one contract per adjacent pair, specified only when both operators are
present. When a project omits an operator the chain collapses: with no preflight,
develop hands straight to sysop. See [docs/contracts.md](docs/contracts.md).

- **develop to preflight**: the deployable artifact and its config surface.
- **preflight to sysop**: the scoped deployment plan, carrying the artifact forward.
- **sysop to petard**: the continuously refreshed operational index.

## Knowing if it worked

Prebuilt-binary distribution fails silently: the long-tail gaps leave the user
thinking it installed when it did not transfer. Hoistable makes success measurable at
two moments of truth. **Before** the deploy, preflight probes the target and predicts
feasibility, so the user learns at the door whether this is going to work. **After** it
runs, the config rebuilds the app's acceptance test on the actual target and prints an
honest transfer score per check, saying plainly what did not transfer. No silent
success.

That transfer score is a normalized number, so it is also the gradeable output a
downstream measure can aggregate across context, user, harness, and model, a
leaderboard or an Agent Dyno run. Hoistable emits the number; it never depends on the
thing that grades it. This is the same envelope as skillc (recipe, rebuild on install,
self-test, honest score), carried by every hoistable config rather than published as a
separate scoring skill.

## The non-destructive onboarding invariant

Onboarding an app onto a target never mutates or collides with anything already
there. Hoisting an app is not re-running the app's own deployment. An app's bundled
orchestration assumes it is the only instance on the box, so replaying it on a host
that already runs the app would stomp the live one. Instead, every hoist deploys into
a fresh namespace the runner owns: its own name, its own host ports, its own storage.
The runner verifies that namespace is empty before it deploys, tears it down when
done, and refuses to deploy at all if a profile does not declare how it isolates. A
profile that genuinely touches no shared state, such as a hermetic self-test in a
throwaway clone, must say so on purpose, with a reason. There is no silent path that
deploys without isolation.

This is enforced in the grader, not left to each config to remember. It was learned
the hard way: a first EAF hoist replayed EAF's own compose, whose fixed project name
and host ports made a fresh clone attach to a live `enterprise-ai` stack and recreate
its containers. The invariant exists so that can never happen again.

## Distribution and repeatability

The primary channel is a skill: a hoistable project distributes itself as its
Layer 2 config, and installing the project means installing that config. The config
does not vendor the operators; it **pins a version** of each operator skill and
pulls it from the Layer 0 release. Repeatability comes from the pin: the same config
resolves to the same operators every time. Isolation still holds, because upgrading
Layer 0 does not touch a config until its owner chooses to bump the pin. There is one
pinned version line, not one per operator.

`SKILL.md` is this skill in its Claude Code form; the same method ports to other
*agent* harnesses behind a thin adapter. The channel is always a skill an agent
invokes, never a command line. The neutral core (`envelope.py`) is the small stdlib
code the skill's agent calls to *enforce* the invariants — isolation, honest grade,
teardown — enforcement behind the skill, not a driver anyone runs.

Hoistable is its own first consumer: it distributes its operators as skills, and the
petard ships inside the config while its execution path stays frontier-independent.

## Build rules

How the operators get built ([docs/build-rules.md](docs/build-rules.md)): ship source
not binary; neutral core, thin adapters; liftable and complete by reference; federated
by pinned version line; converge don't accrete; point don't embed; no silent success;
plain copy. First practiced in agent-dyno.

## Relation to Agent Dyno

Different jobs, shared build rules. Agent Dyno **measures** how efficiently a harness
turns tokens into surviving work. Hoistable **manufactures and operates**. The
relation is one-way: the dyno can measure a Hoistable run; Hoistable never depends on
the dyno.

## Working on Hoistable

The **operating posture** — how to think while building this, not just what it is —
is `CLAUDE.md`. It is short and load-bearing: you are the operator (the four roles are
agent roles, not programs); resolve against the target and author missing pieces
just-in-time rather than pre-building a menu; grade against reality; state plainly what
is built-and-tested versus designed. Read it before adding to the repo.

## Status

Working core with a live frontier, graded against real infrastructure.

**Built and tested (against real dind, a real k3s cluster, a real sandbox):** the
honest-grade envelope; the isolation substrate as a resolved bind, with three rungs
each *authored by the loop* — `dind` (environmental), `k3s` (cluster), `systemd`
(confined); the operators, with sysop's operate/LOM driver and petard's grounded,
refuses-to-invent translation; `hoist` (preflight + deploy + grade); the app **bundle
builder** (ships itself, self-grades on a clean target, pins operators rather than
vendoring); the **resolution store** (persist and share a resolution as a replayable
recipe). honcho hoists build → run → LOM end to end in a sandbox; a dispatched sysop
authored a new rung by skill, proving the loop is a skill an agent runs, not a script.

**Designed, not yet built** (see `docs/ops-substrate.md`): the resolver **strength
model** (host-safety vs infra-type, so authored rungs like k3s/systemd become
*resolvable*, not just usable); the **cost spine** (estimate → reconcile → no silent
spend); the ops substrate as a hoisted rung (build infra up from the primordial); cloud
rungs; the operator release + index.
