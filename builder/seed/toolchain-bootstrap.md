## Get the hoistable toolchain (self-extract, once)

This skill ships as source: it carries the pin to the hoistable toolchain and the recipe
to unpack it, like a self-extracting archive. Before you do anything else, self-extract
the toolchain on this target — and only after verifying it.

1. Read the toolchain pin below (`version`, `url`, `sha256`).
2. Fetch the tarball at `url`, compute its sha256, and confirm it equals the pin's
   `sha256`. If it does not, STOP — never unpack or run an unverified toolchain.
3. Extract the verified tarball. It yields the neutral-core toolchain you *invoke*:
   `builder/emit.py` (the deterministic skill emitter), `release/build_release.py` (build
   a harness kit to pin), and the harness itself — `envelope/` (the enforced grader:
   isolation, honest grade, teardown), `hoist/` (discovery + pin resolution), and the
   `operators/`. None of this is a command a user runs; it is enforcement you call.

Because you checked the sha256 by hand before unpacking, nothing unverified executes.
With the toolchain extracted, follow the method below.

### Toolchain pin

```json
<pin>
```

---
