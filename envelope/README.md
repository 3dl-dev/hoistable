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
      "isolation": {                             // required for any profile that deploys
        "namespace_env": "COMPOSE_PROJECT_NAME", // runner sets this to a unique hoist-<app>-<id>
        "port_envs": ["GATEWAY_PORT"],           // runner assigns each a free host port
        "collision_probe": "test -z \"$(docker ps -aq --filter label=com.docker.compose.project=$COMPOSE_PROJECT_NAME)\"",
        "teardown": "docker compose --env-file .env down -v"
      },
      "preflight":  [ { "name": "docker-daemon", "probe": "docker info", "required": true } ],
      "bringup":    [ { "name": "compose-up", "run": "docker compose up -d …" } ],
      "health":     [ { "name": "postgres", "check": "pg_isready -h localhost" } ],
      "acceptance": [ { "name": "roundtrip", "check": "curl … | grep -q ok" } ]
    }
  }
}
```

A hermetic profile that starts no daemons, binds no host ports, and writes no shared
state declares `"isolation": {"none": true, "why": "..."}` instead.

## Where a hoist runs: the substrate, resolved not depended on

The grader does not care *where* the config's steps run. That "where" is a resolved
bind, the same verb the rest of Hoistable runs on (a config ref resolves
path→index→URL, operators resolve pin→local, a secret resolves on the target).
Isolation is the same: a profile names the *strength* it needs, and the runner
resolves the strongest rung the target actually offers.

```jsonc
"isolation": { "require": "environmental" }   // or omit / "host" for the floor
```

- **`host` (default)**: run on this machine. The isolation is only as strong as the
  config's own declared namespace (`namespace_env` + `port_envs`), so a deploy that
  ignores it can still reach host state. This is the floor rung, and today's behavior.
- **`environmental`**: run where a deploy *cannot* reach host state, whatever the
  config declares. The runner resolves down a ladder (dind here; rootless podman, a
  user-namespace sandbox, a burnable VM, a k3s Job are the next rungs) and provisions
  the first that answers. A file the deploy writes lands in the throwaway container; a
  container it starts or kills lives on an inner daemon the host never sees. Teardown
  destroys the substrate, and the environmental blast radius is verified by the
  substrate's own residue: after teardown no host resource of ours remains. This is
  checked one level up from the config's own isolation, so it holds even for a config
  that ignores that block, and it is scoped to our footprint rather than a full
  host-daemon diff, so unrelated containers churning on a shared host never register
  as a false violation.

If an environmental rung is required and none resolves on the target, that is a
`cannot-build`, named at the door — an unresolved bind, not a crash. See
`substrate.py`; a new rung is a new adapter there, never a fork of the grader
(build-rule 2), and the knowledge of how to drive it lives in the adapter, not here
(build-rule 6, point don't embed).

- **isolation**: the non-destructive onboarding invariant, enforced here rather than
  left to each config. A profile with `bringup` MUST declare isolation. The runner
  owns a fresh namespace (`namespace_env` set to a unique `hoist-<app>-<id>`, each
  `port_envs` var assigned a free host port), verifies it is empty via `collision_probe`
  before deploying, and runs `teardown` when done. A deploying profile that declares no
  isolation is refused, not run. This is why a hoist can never re-assert an app's own
  singular deployment on a host that already runs it.
- **binds**: a missing required bind is a `cannot-build`, named, and the run stops at
  the door. This is `hoist`'s "cannot-build: a required bind is missing, by name."
- **preflight**: cheap probes run before deploy, so the user learns early. A required
  preflight blocker is also a `cannot-build` (fail at the door, not three services in).
- **bringup**: clone, configure, deploy the chosen profile. The install gate.
- **health**: is it actually up. Counted N of M; a partial gate is an honest-failure.
- **acceptance**: the held-back checks. Their pass fraction is the honest transfer
  score. Acceptance runs only when the install gate is fully up, so the score measures
  a system that actually came up, not one that half-started.

## Outcomes

Exactly skillc's three, applied to a deployable system:

- **built**: install gate up and every acceptance check passed.
- **honest-failure**: it came up but something did not transfer; the report names each
  `bringup:` / `health:` / `acceptance:` item that failed.
- **cannot-build**: a required bind or a preflight blocker is missing, named.

## Where pins and operators fit

This runner grades. In the full picture the config also carries its operator pins
(URLs into the Layer 0 release) and its binds map to the external skills sysop composes.
The grader is the acceptance backbone the operators plug into; it is deliberately small.
