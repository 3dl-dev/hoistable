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

## Relationship to what is built

Built: the local/dind rung, the resolution store, the honest grade. This record is the
direction for the operational phase, sequenced after the honcho end-to-end loop (which
closes build to run to LOM on one app and forces the first cut of OPERATE mode).
