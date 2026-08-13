# Operational model: the ops substrate is a hoisted rung

Design direction for the operational phase, captured 2026-08-13. This is forward
direction (invariants, model, open decisions), not a frozen conclusion. Re-derive the
live parts every time.

## Thesis extension

Hoistable hoists at more than one level. The ops substrate (the infra: a VM host, a
cluster, DNS, backups) is a rung ABOVE apps, hoisted and operated by the same
machinery. It is not given, not external, not untouchable. Infra did not come from the
aether; it got built, and hoist is what builds and operates it.

## Invariants (checked every time, never remembered)

1. **Touchable from local.** Any infra rung, however high, stays operable from a bare
   local position. You never lose the ability to run and fix it from your laptop.
   petard/LOM is this guarantee at the infra level: operate your ops substrate locally
   and independently, even with the cloud or the frontier down. An infra rung you
   cannot touch from local is the failure mode.
2. **Nudge, not lane.** Infra setups are offered as known-good recipes to start from
   and diverge, never as a taxonomy that classifies and constrains. Default to the
   simplest viable rung; keep "author your own" first-class; a recipe is re-resolved to
   reality on replay, never trusted. If the library is so thin everyone lands on one
   setup (e.g. proxmox/k3s), the taxonomy has snuck back in the side door.
3. **Recipes re-resolve, never freeze.** A recipe (infra recipes included) is a
   replayable resolution; replay re-probes and re-resolves; the snapshot is a hint.
   (See hoistable-543 and hoistable-5e8.)
4. **rd is not a product dependency.** rd is how we build Hoistable. Hoistable ships and
   depends on neither rd nor any specific coordination tool. Product-level coordination
   is the resolution store plus dependencies among recipes. Any coordination tool is a
   resolved slot-in, never assumed.
5. **State does not re-derive.** App data and cluster state are one-way facts. Growing
   or moving must migrate state, and that is sysop's real backup and state
   responsibility. Everything else re-derives; data does not.
6. **No silent spend.** Every resolution, deploy, and practice-run surfaces its
   estimated and actual cost; spend is gated proportionally by operator policy, never
   hidden. This is no-silent-success applied to money, and its teardown guarantee is
   the residue check (invariant on the substrate) pointed at billable resources.

## The model

- The **primordial is bare**: a machine, local docker, maybe nothing. Not k3s.
  proxmox/k3s is one chosen ops substrate, not universal, not primordial, not the only
  viable one (a single docker host, a cloud managed service, fly.io, Nomad all qualify).
- A substrate rung is either **found** (docker is here, resolve against it) or **built**
  (no k3s, hoist provisions it). Building a rung IS a hoist: the ops platform is a
  hoistable whose "app" is the platform. `develop` authors it, `sysop` stands it up and
  operates it, `petard` runs it lights-out. The same generic roles, one level down.
  That is "provide its own", recursively.
- An ops substrate is **its own recipe in the store**. App recipes resolve to / depend
  on it; it resolves down to a lower substrate (proxmox to VMs to bare); the chain
  bottoms out at the primordial.
- **Centralization is operating the shared infra rung**, not a control tool. The infra
  rung is what N apps have in common; operating it is the central control, and every app
  on it is operable through it because they share it.
- Three distinct things, kept apart:
  - **manifest** = what you have (re-probed every time)
  - **policy** = what you want or forbid (persisted preference, preflight, contract B)
  - **recipes** = what has worked (proven starting points, the nudge)
  preflight matches recipes against manifest and policy and recommends the simplest
  viable one, always re-resolved to your hardware and always overridable.

## Adoption: back into the sophistication

Start with an app in local docker (primordial, no infra rung). When you outgrow it,
hoist an infra rung: a single cloud VM docker host, then k3s plus DNS plus backups.
Apps re-resolve UP onto it. Infra grows underneath, hoisted from the primordial, as
needed. You back into the sophistication; you never assume it.

Why this needs sharing (hoistable-5e8): a newcomer cannot invent a good k3s setup, they
do not know what it is. A shared infra recipe is how that hard-won expertise travels:
they pull a proven resolution, re-resolve it to their laptop, and get a working server
without knowing k3s. Infra recipes are the highest-value thing to share.

## New surface this opens (not free)

- **Recipes depend on recipes.** An app's substrate is another recipe (the infra). The
  store needs a dependency notion among recipes.
- **sysop operates something long-lived.** An infra rung persists and must be run;
  grade-and-teardown (what the envelope does today) is not operate. An OPERATE mode,
  distinct from the GRADE mode, is required. This also surfaces immediately in the
  honcho end-to-end loop: petard must harvest from a deploy that stays up.
- **State and cluster migration** is sysop's backup responsibility.
- **MVP ladder:** local docker (built) -> single cloud VM docker host -> k3s/proxmox as
  the sophisticated end, not the MVP.

## The rung is resolved just-in-time (the ladder is a cache, not a menu)

A substrate rung is not a pre-built adapter picked from a fixed set. It is resolved
just-in-time by AUTHORING it against the `{provision, exec, teardown, workroot,
strength}` contract when the operator's problem needs it. The checked-in ladder (dind,
today) is a warm cache of already-authored rungs, not the boundary of what is
resolvable. The frontier is "anything develop can author to satisfy the contract,
matched to this operator's reality" -- k3s, EKS, AKS, a DigitalOcean droplet: each
authored on demand, not enumerated in advance. Building a rung "now" pre-builds a menu
item and contradicts the point; the rung is built when an operator's problem scope
requires it.

This is build-rule 1 (ship spec + generator + acceptance test; checked-in code is a
regenerable reference build), applied to substrates:

- **spec** = the `{provision, exec, teardown, workroot, strength}` contract
- **generator** = develop, authoring an adapter against it, matched to need
- **acceptance test** = the honest-grade envelope: a JIT-authored adapter is GRADED on
  the real target, so we learn honestly whether it works, not whether it looked right
- **reference build** = dind (the shape the generator learns from)

The surrounding machinery already makes JIT viable: the grade validates the authored
adapter at runtime (JIT without a validator is guessing); the resolution store (5e8)
caches the validated adapter as a shareable recipe, so the nudge library warms itself
(JIT the first time a k3s operator appears, cache-hit after); petard operates whatever
got authored. The deploy profile is a coupled axis authored alongside the rung: an app
that deploys with docker compose needs a k8s profile to target a cluster rung, so
develop authors both against the operator's need.

Governance: safe to fully automate for a throwaway rung (dind, a droplet you own and
can burn). For anything that spends, persists, or is hard to reverse, the loop is match
need -> PROPOSE the adapter and its spend -> preflight scopes it with the human ->
approve -> author, grade, cache. The model is JIT; the governance is preflight and
policy, gated proportionally at cost.

## Cost spine: no silent spend

Cost is a first-class quantity we surface, not a wall. A throwaway EKS practice run that
tears down is cents ($0.34, not a scary bill); treating cents with the ceremony of a
persistent commitment is the wrong kind of boxing-in. So the gate is a PROPORTIONAL
DIAL set by operator policy (auto under $X, ask above, never-persistent-without-
approval), not a binary, and the standing obligation is transparency.

Where it lives:

- **preflight / policy** carries the operator's spend tolerance and the estimate in the
  feasibility verdict ("practicing ~$0.34, running ~$40/mo -- proceed or ask?").
- **the envelope's grade extends to honest-cost**: predicted vs ACTUAL, reconciled after
  the run, calibrating the recipe. Cost is re-derived from real runs, never frozen.
- **the nudge library carries cost profiles** and leans into efficient practices we have
  used: local hardware first (free -- the floor of the ladder), scale-to-zero (Azure
  Functions, elastic ACS) over always-on, managed (AKS/EKS) over hand-rolled, inference
  APIs (Bedrock, Deepinfra) over renting GPUs. Cheapest-viable-rung is the resolver
  default -- "simplest viable rung" with a price tag; the free floor means we climb to
  paid rungs only when the need pays for it.

The honesty transparency demands (the engineering, not the intent):

1. **Estimate with a range and confidence.** An estimate of $0.34 that bills $50 is a
   transparency failure, worse than none. First-run estimates for a JIT-authored adapter
   are guesses; say so.
2. **Reconcile predicted vs actual** after each run and calibrate the recipe. The grade
   loop, applied to the bill.
3. **Verified teardown is the residue check pointed at money.** "Fully tear it down" only
   holds if teardown is reliable; a failed teardown turns a 34-cent experiment into a
   monthly leak. For a cloud rung, RESIDUE = leftover BILLABLE resources. The same
   mechanism that proves dind left no container proves EKS left no billable node.

The JIT loop with its cost spine: match need -> author adapter -> estimate (range) ->
surface and gate proportionally -> run -> grade AND reconcile the bill -> verified
teardown (residue = no cost leak) -> cache the recipe with its calibrated cost profile.

## Relationship to what is built

Built: the local/dind rung, the resolution store, the honest grade. This record is the
direction for the operational phase, sequenced after the honcho end-to-end loop (which
closes build to run to LOM on one app and forces the first cut of OPERATE mode).
