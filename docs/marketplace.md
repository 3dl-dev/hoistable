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

A developer's `/hoistable:build` scaffolds a one-plugin marketplace in their own repo (`emit.scaffold_marketplace`). Their users run `/plugin marketplace add their/repo` and invoke `/their-app:<their-verb>`. They pick the plugin name, the skill verb, and the description, and the defaults carry none of our naming. The only tie to us is the harness pin URL, and they can host their own harness (`emit --kit <tgz> --kit-url <their-url>`) to depend on nothing of ours.

## What a skill carries

One self-building `SKILL.md`. It carries the app's recipe inlined, a pin under `operators` (`version`, `url`, `sha256`), and the receiver-side steps stamped in: verify the pin's sha256 by hand, unpack the runtime, resolve the substrate, deploy through the enforced grader, and report built, honest-failure, or cannot-build. The runtime comes from the pin. Both repos are public, so the pin resolves over plain HTTPS with no auth.

## A frontmatter gotcha worth remembering

Skill descriptions are quoted in the frontmatter so a colon cannot break the YAML. An unquoted `: ` in a description makes Claude Code silently drop the skill, which cost real debugging time twice. `emit.py` quotes it, and a test guards it.

## Re-cut a release

1. Build the kit: `core/release/build_release.py` gives `hoistable-operators-<v>.tgz` (harness plus builder plus release tooling).
2. Publish it: `gh release create operators-v<v> <tgz> --repo 3dl-dev/hoistable`.
3. Regenerate the tool plugins pinned to it: `core/release/build_plugins.py --pin <pin.json>` (single source; never hand-edit `plugins/`). Re-emit each registry app skill with `core/builder/emit.py --kit <tgz> --kit-url <release-asset-url>`.
4. Bump the versions in both `marketplace.json` files, commit, and push.
