# Distribution: two repos, two verbs

Hoistable ships as Claude Code plugins, agent-first. Two public repos.

## The tools: 3dl-dev/hoistable

    /plugin marketplace add 3dl-dev/hoistable
    /plugin install hoistable@hoistable

One plugin, `hoistable`, with two skills:

- `/hoistable:build` turns your app into a self-installing skill.
- `/hoistable:run` installs and grades a recipe someone handed you.

This is the only place our name shows. It is our tool, and only a developer building with it sees it.

## The tap of tested apps: 3dl-dev/hoistables

    /plugin marketplace add 3dl-dev/hoistables
    /plugin install agent-dyno@hoistables

Each app is its own plugin, named after the app, with a neutral `deploy` skill:

- `/agent-dyno:deploy`, `/honcho:deploy`, `/hoistable:deploy`.

No framework verb or wording lands on any product. One plugin per app means a self-hosted app never collides with ours or anyone else's. Naming a third-party app here is descriptive, like a Homebrew tap; it does not imply affiliation.

## Self-hosting, us invisible

A developer's `/hoistable:build` scaffolds a one-plugin marketplace in their own repo (`emit.scaffold_marketplace`). Their users run `/plugin marketplace add their/repo` and invoke `/their-app:<their-verb>`. They pick the plugin name, the skill verb, and the description, and the defaults carry none of our naming. The emitted skill carries nothing of ours (no toolchain, no pin), so a developer who self-hosts depends on nothing of ours: the one file is entirely theirs.

## What a skill carries

One self-contained `SKILL.md`. It carries the app's recipe inlined and the honest-grade discipline stamped in as prose: the receiver's agent resolves the isolation, clones, deploys in a sandbox, checks health, runs the held-back acceptance, tears down, and reports built, honest-failure, or cannot-build. It pins no toolchain and carries nothing to fetch or run, there is no runtime of ours. The receiver's agent does the whole hoist in its own session with ordinary tools.

## A frontmatter gotcha worth remembering

Skill descriptions are quoted in the frontmatter so a colon cannot break the YAML. An unquoted `: ` in a description makes Claude Code silently drop the skill, which cost real debugging time twice. `emit.py` quotes it, and a test guards it.

## Re-cut a release

There is no kit to build or publish: the skills carry nothing to fetch or run.

1. Edit the sources (`core/builder/SKILL.md`, `core/hoist/SKILL.md`) and regenerate the tool plugins: `core/release/build_plugins.py` (single source; never hand-edit `plugins/`).
2. Re-emit each registry app skill from its config: `emit.emit_skill(config)` writes a self-contained `<app>.hoist.SKILL.md`.
3. Bump the versions in both `marketplace.json` files, commit, and push.
