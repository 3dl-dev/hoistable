# The honest-grade envelope

`envelope.py` is the neutral core of build-rule 7 (no silent success). It takes a
Layer 2 config, hoists the app onto a target the way the config says, and grades the
result honestly. It is standard library only and app-agnostic: every app specific
lives in the config, never in the runner.

## Run

```
python3 envelope/envelope.py <config.json> [--profile NAME] [--target-dir DIR] [--json-out FILE]
```

With no `--target-dir` it hoists onto a fresh temp dir, so a run is a clean-target
run by default. Exit code: `0` built, `1` honest-failure, `2` cannot-build.

## Config schema

A config is JSON. It is the app's Layer 2 formula as far as the grader is concerned:
what to pull, what the target must provide, and how to know it worked.

```jsonc
{
  "app": "name",
  "source": { "clone": "URL-or-local-path", "dir": "subdir" },  // omit to grade in place
  "binds": [                                   // required local capabilities
    { "name": "docker", "probe": "docker version", "required": true }
  ],
  "default_profile": "minimal",
  "profiles": {
    "minimal": {
      "preflight":  [ { "name": "port-free", "probe": "…", "required": true } ],
      "bringup":    [ { "name": "compose-up", "run": "docker compose up -d …" } ],
      "health":     [ { "name": "postgres", "check": "pg_isready -h localhost" } ],
      "acceptance": [ { "name": "attribution", "check": "pytest tests-live/…" } ]
    }
  }
}
```

- **binds** — a missing required bind is a `cannot-build`, named, and the run stops at
  the door. This is `hoist`'s "cannot-build: a required bind is missing, by name."
- **preflight** — cheap probes run before deploy, so the user learns early. A required
  preflight blocker is also a `cannot-build` (fail at the door, not three services in).
- **bringup** — clone, configure, deploy the chosen profile. The install gate.
- **health** — is it actually up. Counted N of M; a partial gate is an honest-failure.
- **acceptance** — the held-back checks. Their pass fraction is the honest transfer
  score. Acceptance runs only when the install gate is fully up, so the score measures
  a system that actually came up, not one that half-started.

## Outcomes

Exactly skillc's three, applied to a deployable system:

- **built** — install gate up and every acceptance check passed.
- **honest-failure** — it came up but something did not transfer; the report names each
  `bringup:` / `health:` / `acceptance:` item that failed.
- **cannot-build** — a required bind or a preflight blocker is missing, named.

## Where pins and operators fit

This runner grades. In the full picture the config also carries its operator pins
(URLs into the Layer 0 release) and its binds map to the external skills sysop composes.
The grader is the acceptance backbone the operators plug into; it is deliberately small.
