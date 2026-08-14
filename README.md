# Hoistable

Ship software as a skill that installs itself.

## The problem

Handing software to someone else is where it breaks. You send a repo or a binary, and on their machine the config is different, a service is missing, a port is taken, or it just "works on mine." Every install turns into someone bridging that gap by hand. Prebuilt packages don't fix it; they hide the gaps until the thing is already running wrong.

## How it works

You ship a recipe, not a build. The recipe is a skill: a Markdown file an agent reads. When someone installs it, their agent runs it on their machine. It clones the project, configures it, deploys it, then rebuilds the project's own tests on that machine and reports an honest score of what worked and what didn't. Nobody types a command. The agent does the work and tells you plainly whether the software transferred.

There are two verbs:

- **hoist** — run a distributable into a live, graded system on your target.
- **hoistable** — turn your own app into that distributable in the first place.

`hoistable` makes what `hoist` runs.

## Use it

Add the marketplace once (Claude Code):

    /plugin marketplace add 3dl-dev/hoistable

### Run software someone shipped

If someone hands you an `<app>.hoist.SKILL.md`, or drops one into your skills folder, ask your agent to hoist that app. It fetches a checksum-verified harness, brings the app up in a throwaway sandbox on your machine, runs the app's own tests there, and reports the score. Nothing you already have running is touched.

Tested wraps of other people's apps live in a separate registry, not in this repo.

### Ship your own software

    /plugin install hoistable@hoistable

Point it at your repo and ask it to make your app hoistable. It writes the config with you, emits one `your-app.hoist.SKILL.md`, and grades it on a clean target so you know it stands up somewhere other than your laptop. Publish that one file anywhere: a GitHub release, your own marketplace, or straight into someone's skills folder.

### Hoist a config directly

    /plugin install hoist@hoistable

Point `hoist` at a config or a `.hoist.SKILL.md` and it deploys and grades it, no marketplace needed.

### Other agent harnesses

The `SKILL.md` file is the whole unit. Any harness that reads `~/.claude/skills/` (OpenCode, and others by that convention) takes the same file. Drop it at `~/.claude/skills/<name>/SKILL.md`. The plugin marketplace is the Claude Code convenience on top of that.

## What you get

- **An honest answer.** The install rebuilds the app's acceptance tests on your machine and prints what passed and what failed. A hoist that cannot say it worked says what didn't instead. No silent success.
- **No collateral damage.** Every hoist runs in a namespace the runner owns and tears down after, and it refuses to deploy at all unless a profile declares how it isolates. It will not replay an app's own deployment over a copy you already run.
- **Nothing trusted blindly.** The skill names its harness by URL and sha256. The receiver fetches it, checks the hash, and only then runs it.

## Under the hood

A hoist is carried out by four operator roles the skill carries: **develop** extends the app, **preflight** scopes the deploy and predicts whether it will work, **sysop** deploys and operates it (composing whatever infra skills the target needs), and **petard** is a local, frontier-independent fallback so you can still operate when the cloud or the model is down. The Python in the repo (`envelope/`, `hoist/`, `builder/`) is the neutral core the skill's agent calls to enforce the guarantees above. It is not a command line. The skill is the interface.

For depth: `docs/operator-model.md` (the modes and the operators), `docs/contracts.md` (how the roles hand off), `docs/ops-substrate.md` (running real infrastructure), `docs/marketplace.md` (publishing), and `CLAUDE.md` (how to build here).

## Status

Working core, graded against real infrastructure rather than mocks.

Built and tested: the honest-grade envelope; isolation as a resolved bind, with three rungs the loop authored itself — `dind` (throwaway container), `k3s` (cluster), and `systemd` (confined); the four operators; `hoist` and `hoistable`; and the marketplace, with honcho and agent-dyno hoisting to a clean score end to end. A weaker model on a different harness (OpenCode driving a local Qwen) installs and self-extracts the skill; driving that model all the way to a graded deploy is still open.

Designed, not built (see `docs/ops-substrate.md`): the resolver strength model, the cost spine (estimate, reconcile, no silent spend), and building infrastructure up from a bare machine.
</content>
