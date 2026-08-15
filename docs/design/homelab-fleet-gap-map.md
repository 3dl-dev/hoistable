# Gap map: hoisting a real homelab fleet

Date: 2026-08-15. Source: a homelab dashboard screenshot (a Homepage/Homarr-style
board, ~60 tiles) shared as the target. The ask: *what would it take for Hoistable to
build and manage all of them, for one operator, from a single repo.*

This is a **gap map against the honest built state**, not a plan of record. Every row is
tagged built+tested / designed / missing, grounded in `docs/operator-model.md`,
`docs/contracts.md`, `docs/ops-substrate.md`, `core/`, and the two real grades in
`docs/design/honcho-*.md`. It does not descope anything; it says where the product stands
versus this target so an operator can decide what to build next.

## What the target actually is

The board is not a set of independent apps. It is a **heterogeneous fleet-of-record**:
the operator's *real* production instances, spanning containers, appliances, and cloud
accounts, wired to each other. The single-repo, single-operator framing is the ask; the
wiring and the "of record" part are what make it hard.

The ~60 tiles split into four classes with **very different hoist profiles**. This split
is the first finding: "build and manage all of them" is not one problem.

| Class | Count | Examples | Can Hoist *build* it? | What "manage" means |
|-------|-------|----------|----------------------|---------------------|
| **A. Off-the-shelf containers** | ~30 | Plex, Immich, Paperless, Gitea, Trilium, Radarr/Sonarr/Prowlarr/Bazarr, qBittorrent, Open WebUI, Uptime Kuma, Grafana, Portainer, Dozzle, Pi-hole, Syncthing, Guacamole, NPM, HealthChecks, Hoarder, code-server | **Yes** — the "app → hoist skill" path. This is the built path. | deploy + operate + keep running via sysop/petard |
| **B. Appliances / hardware-bound** | ~11 | Proxmox, Proxmox Backup, pfSense, UniFi, QNAP, PiKVM, IPMI, APC UPS, printer, scanner | **No** — existing hardware/appliances; nothing to `git clone` and `compose up`. | manage/monitor/back-up only (sysop/petard against an API/appliance) |
| **C. SaaS / cloud accounts** | ~9 | Cloudflare, Tailscale, Backblaze, AWS, Google Admin, ProtonVPN, GitHub, Claude, OpenRouter | **No** — not self-hosted at all. | API-driven config-as-skill (DNS records, VPN ACLs, backup targets) |
| **D. Custom / niche** | ~9 | MinusPod, Audicle, Paperless-GPT, Huntarr, PixelProbe, Dead-Drop, Pulsarr, PhotoShare, PlexStats | **Yes, but** recipe likely doesn't exist — authored JIT by reading the repo | deploy + operate, same as A once a recipe exists |

Only A and D are genuinely *buildable* by the hoist skill as it stands. B and C are
**manage-only**, and Hoistable today has **no manage-only skill shape** — the whole
discipline is build → deploy → grade (`core/hoist/SKILL.md`). That is Gap 0.

## Where Hoistable actually is (the honest baseline)

- **One real end-to-end grade, ever**: honcho, `score_sonnet = 3/3`, a clean-context
  receiver self-built a dind sandbox, cloned real honcho, `compose up`'d 3 services,
  passed 3/3 health + 3/3 acceptance (`docs/design/honcho-baseline-sonnet.md`). **One
  app, one host, one isolation rung (host-floor + docker-in-docker).**
- **Substrate**: the handle contract `{provision, exec, teardown, workroot, strength}`
  is specified (`docs/contracts.md`), but **only host-floor + dind has ever resolved
  against real infra**. k8s / Proxmox / remote-Docker / cloud are explicitly
  JIT-authored-on-demand, zero grades. The resolution store `hoist/resolutions.py` is
  doc-referenced but **does not exist** in the tree (removed in the skill-only reshape).
- **Fleet coordination**: **designed only** (`ops-substrate.md` invariant 4, "new
  surface this opens"). What exists is independent per-app `config.json` under
  `examples/{honcho,eaf,agent-dyno,hoistable}/`, no cross-app linkage.
- **Operators**: all four exist as prose skills (`core/operators/*/SKILL.md`), but
  `emit.py` puts **no operator content into the emitted app skill** — the Sonnet receiver
  "could not literally point the user at the operators" and improvised. The *manage* half
  of "build and manage" does not travel in the product yet.
- **Cost spine**: designed, not built.

So the built product today is: *turn one Class-A/D compose app into one skill, and grade
one isolated copy of it on dind.* Everything the homelab ask adds beyond that is a gap
below.

## The gaps, ranked by what blocks the ask

### Gap 0 — No manage-only shape for things Hoist did not build
20 of 60 tiles (classes B + C) are appliances and SaaS. Hoist's entire spine is
build→deploy→grade; there is no "adopt and operate a thing that already exists and owns
its own state" mode. For a homelab, *most of the infra layer is this*. **Missing**, and
it is a conceptual addition, not a feature toggle: a sysop/petard-shaped skill whose
acceptance is "I can observe and safely act on an existing endpoint," not "I deployed a
graded copy."

### Gap 1 — Two things wear the word "isolation"; only the demo one is graded
This is the gap that, mislabeled, makes the whole project read as a demo. The correction:
**the isolation discipline is not wrong — it conflates two distinct properties under one
word, and only the wrong one has ever been exercised.**

- **Namespace-of-record**: own a fresh, verified-empty slice (own name, ports, dataset),
  never re-run the app's singleton deploy, never stomp a neighbor. This is **correct at
  every scale**, and it is precisely the primitive that lets one operator run 60 services
  on shared hosts without them clobbering each other. Here isolation *enables*
  fleet-scale operation; it is the precondition, not the obstacle. sysop's spec already
  says exactly this: the host floor "stays running; this is its home... you tear it down
  only for a proof/grade run or a failed deploy, never the live instance."
- **Ephemeral sandbox** (docker-in-docker throwaway): a **grading device** — prove
  transfer, tear down. This is the *only* rung ever graded (both honcho episodes).

So what is actually wrong is narrower and fixable, not "throw out isolation":
1. **Only the sandbox rung has been graded**, so the *shipped* product genuinely is a
   demo — it can prove an app transfers but has never stood one up as the operator's live
   instance. This is the honest cause of "why bother."
2. **The discipline's language over-indexes on ephemerality** ("environmental sandbox,"
   "a deploy must never touch host state," "refuse a profile that declares no isolation").
   Read as *own a verified namespace*, it is right at all scales. Read as *must be a
   throwaway that can't reach host state*, it forbids the production-of-record instance a
   homelab exists to run (Pi-hole binding :53, NPM binding :443, Plex owning its dataset).

**The fix (a posture call, reserved):** make **production-of-record the default terminus**
and sandbox the proof-mode, then **grade the namespace-of-record rung on a real host**.
The alternative — keep sandbox-default and bolt on an explicit promote step — is weaker;
sandbox-as-terminus is what makes hoist read as a toy. Either way, "operating at all
scales" is not in tension with the isolation discipline; the namespacing discipline is the
thing that *makes* N-apps-on-M-hosts safe. What blocks scale is Gap 2 (ungraded substrate
rungs) and Gap 3 (no fleet layer), not isolation.

### Gap 2 — Substrate: only dind resolves; the fleet is Proxmox + many Docker hosts
The board spans Proxmox VMs/LXC, several Docker hosts, bare metal, appliances. **Only
host-floor + dind has ever resolved.** To manage this fleet you need real, graded rungs
for at least: (a) a **remote Docker host over SSH** (the common homelab case), (b)
**Proxmox LXC/VM provision**, and (c) a **target selector** ("which of my N hosts does
this app land on"). All designed-not-built; the resolution store to hold the answers
doesn't exist. This is the single biggest *buildable* gap.

### Gap 3 — No fleet layer (this is the "single repo" ask, verbatim)
"Manage all from one repo, one operator" needs a **fleet manifest / resolution store**
spanning apps, per-app recipe references, and one operator identity + secrets store across
60 services. `ops-substrate.md` names exactly this ("centralization = operating the shared
infra rung") as **designed, not built**. Today: 60 unlinked `config.json`s. This is the
spine the whole ask hangs on.

### Gap 4 — Inter-app dependency graph (the *arr stack is a graph, not a list)
Prowlarr → Radarr/Sonarr → qBittorrent → Bazarr; NPM fronts everything; Pi-hole is DNS
for all; Immich needs Postgres; Tailscale is the network fabric. Hoist recipes are
independent — there is **no recipe-depends-on-recipe** and no **cross-cutting-concern
contract** (shared reverse-proxy registration, shared DNS, shared network, shared DB).
`ops-substrate.md` lists recipes-depending-on-recipes as designed-not-built. You cannot
"build and manage all of them" without ordering and wiring; this is the difference between
60 deploys and *a homelab*.

### Gap 5 — Operators don't travel in the emitted skill (near-term, cheap)
The manage half lives in `core/operators/*` but `emit.py` emits none of it. Even for a
single app, "manage" is not yet delivered through the product surface. **Missing but
small**: emit an operator-handoff section (or per-app operator stubs) into
`<app>.hoist.SKILL.md`. This is the lowest-cost gap and it unblocks the "manage" word for
Class A/D immediately.

### Gap 6 — Fleet continuity (petard is per-command, not a backup orchestrator)
petard composes `arlo` to resolve one grounded command when the frontier is down. A
60-service homelab wants **fleet-wide backup/continuity** (Proxmox Backup + Backblaze +
Syncthing as one policy). Backup-as-a-fleet-concern is unbuilt. Petard's shape is right
for "give me the command"; it is not a scheduler/policy engine, nor should it become one —
this likely wants a petard-adjacent continuity skill that composes the existing backup
appliances (Class B), which loops back to Gap 0.

### Gap 7 — Cost spine (low priority for this target)
Mostly electricity + a few metered cloud accounts (AWS, Backblaze, OpenRouter, Claude).
Designed-not-built. Matters only for the Class-C tier here; not on the critical path.

### Gap 8 — Nothing but a 3-container compose app has been graded
honcho is a clean 3-service compose app. Plex/Immich/the *arr stack are *also* compose
apps (plausibly in-reach), but **zero** have been graded, and appliances/SaaS have **no
grade path at all**. The claim "Hoist can do Class A" is currently *designed-by-analogy to
one grade*, not measured across the class.

## Smallest honest next step

The built path today reaches exactly one place: one Class-A compose app → one skill →
graded on dind. The realistic first move toward the homelab, in dependency order:

1. **Gap 5** (operators travel) — cheap, unblocks the "manage" word for A/D.
2. **Gap 2a** (remote-Docker-over-SSH substrate rung, really graded) + **Gap 1**
   (production profile that the honest-grade blesses) — together these let Hoist put a
   *real* instance on a *real* homelab host, not a dind copy. Prove it with 3–5 Class-A
   apps (e.g. Uptime Kuma, Gitea, Immich, one *arr) graded on an actual host.
3. **Gap 3** (fleet resolution store) then **Gap 4** (dependency graph) — the actual
   "single repo, manage all" work, only worth starting once step 2 has a real grade.

Classes B and C (Gap 0) are a separate track: a manage-only skill shape. Do not fold them
into the build path; they never build.

## What must not drift here

- This is a **skill** deliverable in each case, run in the operator's session against
  *their* fleet. Do not build a homelab-manager program. The 60 skills + a fleet
  resolution store (references, not a runtime) is the shape.
- Grade against the **real fleet**, not a mock. "Class A works" is one honcho grade wide
  until more of the class is measured. Label rungs with the guarantee they earned.
- B and C are manage-only. Saying Hoist will "build" Proxmox or Cloudflare is dishonest;
  it manages them.
