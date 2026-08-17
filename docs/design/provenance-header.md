# Emitted-skill provenance header (PROPOSAL — pending robustness pass)

Ship-clarity move #2 from `hoistable-eab`. Goal: make every emitted skill
**self-declare that it is a per-target cross-compiled artifact with an earned
grade**, so the product itself states the architecture instead of reading as a
generic installer. This is a proposal; implementation waits on the robustness
verdict (decision: robustness first, then this).

## Where it goes

A short prose block at the very top of every emitted `SKILL.md` (canonical and
variant alike), right under the title, before the recipe. Prose, not a comment —
the product is a skill the receiver reads; the header is part of what it reads.

## Format (IMPLEMENTED 2026-08-16, NEUTRAL per decision)

Decision: **neutral**. The header carries NO vendor brand and NO build-tool line,
so the emitted skill stays the developer's own product (the unbranded-output
invariant in `emit.py` + `test_builder.py`). It still self-declares the
cross-compile facts. Source of truth: `emit._provenance_header` and the three
provenance tests in `test_builder.py`. Shipped form:

Variant (cross-compiled for a specific target):

```
> **Skill provenance.** Cross-compiled from a source recipe for one target.
> - **App:** honcho
> - **Cross-compiled for:** model `qwen3.8-27b` · agent `opencode` · environment `environmental`
> - **Reference substrate:** `claude` (the build this target is graded against)
> - **Deltas applied:** `qwen-opencode`
> - **Transfer grade (this target):** not yet measured
```

Canonical (the reference build, no `--receiver`):

```
> **Skill provenance.**
> - **App:** honcho
> - **Build:** reference (canonical): strong-model default, model unpinned; environment `environmental`
> - **Deltas applied:** none (shared core only)
```

No "Hoistable", no "emit.py", no filesystem path (dropped for neutrality and
determinism). The target triple comes from a `<!-- target: model=.. agent=..
reference=.. -->` line in the delta file, stripped from the shipped body. The
grade defaults to "not yet measured"; `emit --graded "<text>"` stamps a measured
result verbatim (never a fabricated number).

## emit.py wiring

Build-time fields emit already knows or can read:
- **app** — `config.app`.
- **environment** — `profile.isolation.require`.
- **deltas applied** — from `--receiver` (none for canonical).
- **source** — the spec path.

New: the receiver profile must carry its **triple metadata** so emit can name the
model and agent. Add a small metadata block to each delta file that emit parses
(kept next to the corrections it already stamps):

```
<!-- hoistable:target model=qwen3.8-27b agent=opencode reference=claude -->
```

`_receiver_delta()` already loads the delta file; extend it to also return this
target metadata for the header. No new files, no registry — the delta file is the
single source of truth for its own triple.

**Grade field — honest by construction.** emit does NOT know a transfer score
(that is measured later by an episode). Default the field to **"not yet
measured"** — never a fabricated number. An optional `emit --graded "<text>"`
stamps a measured result (the ouroboros grader can pass what it recorded, e.g.
from `docs/design/corpus/<app>.md`). A skill that claims a grade it did not earn
is exactly the dishonesty the whole project guards against, so the default must be
the honest blank, and the number only appears when a real episode produced it.

## Why this is the highest-leverage clarity move

The header turns the architecture from something you read in `docs/` into
something stamped on the artifact: anyone holding an emitted skill sees the target
triple, the deltas, and the earned (or explicitly unmeasured) grade. It makes the
cross-compiler model unmissable at the exact surface where the old "app-installer"
misreading happens — the emitted skill itself.

## Tests to add (with implementation)

- Canonical emit stays byte-stable except for the header block; header names
  reference substrate, `deltas: none`.
- Variant header names the correct triple parsed from the delta metadata.
- Ungraded emit renders "not yet measured" (never a number); `--graded` stamps the
  passed text verbatim.
- Round-trip: `extract_config` still recovers the carried recipe with the header
  present.
