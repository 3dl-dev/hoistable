# The hoistable marketplace

`3dl-dev/hoistable` is a Claude Code plugin marketplace. It distributes **self-building
hoist skills**: you install a skill, and on first use your agent self-extracts the
verified harness from a pinned release, hoists the app onto *your* target, and grades it
with an honest transfer score. Agent-first — nobody runs a command line. It includes
**hoistable itself**.

## Add it, install a skill (Claude Code)

    /plugin marketplace add 3dl-dev/hoistable
    /plugin install honcho@hoistable        # ship honcho onto your target
    /plugin install hoistable@hoistable     # hoistable itself, as a hoist skill

Then just invoke the skill; it self-builds before it reports the app is up.

The repo is **private**, so `gh` auth is used to fetch it and its release assets
(`hoist/pins.py` fetches release assets via `gh`, which authenticates for private repos).
For distribution to machines without access to this org, the repo and the operator-kit
release must be public — an exposure decision.

## What a plugin carries

Each plugin is one self-building `skills/<name>/SKILL.md`. It carries:

- the app's Layer 2 recipe (inlined) and the **operators pin** (`version`, `url`,
  `sha256`) — the URL points at the kit published as a release asset on this repo;
- the receiver-side hoist recipe, stamped verbatim: verify the pin's sha256 by hand →
  unpack the harness → resolve the substrate → deploy through the enforced grader →
  report `built` / `honest-failure` / `cannot-build`.

Nothing else is needed on the receiver; the harness comes from the pin.

## Other harnesses

The portable unit is the `SKILL.md` file. Harnesses that read `~/.claude/skills/`
(OpenCode, and others by convention) take the same file dropped at
`~/.claude/skills/<name>/SKILL.md`. The `.claude-plugin/marketplace.json` install layer
is Claude Code specific; the skill file itself is universal.

## Re-cutting a release

The plugin skills pin a kit release. To cut a new one:

1. Build the kit: `release/build_release.py` → `hoistable-operators-<v>.tgz`.
2. Publish it: `gh release create operators-v<v> <tgz> --repo 3dl-dev/hoistable`.
3. Re-emit each plugin skill pinned to it:
   `builder/emit.py <app-config> --kit <tgz> --kit-url <release-asset-url>` →
   `plugins/<app>/skills/<app>/SKILL.md`.
4. Bump the plugin `version` in `.claude-plugin/marketplace.json`, commit, push.

`builder/emit.py --kit` derives the pin (sha256 of the real bytes + the resolvable URL),
so a shipped skill never carries a dangling pin.
