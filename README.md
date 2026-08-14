# Hoistable

Hand your software to someone and have it actually run on their machine.

Software works where you built it and breaks everywhere else. The config is different, a service is missing, a port is taken. Whoever installs it ends up fixing all that by hand. A prebuilt package doesn't help. It just hides the breakage until the thing is already running wrong.

Hoistable ships the recipe to stand your software up, not a finished build. You hand over one file. When someone installs it, their agent runs it for them. It clones the project, sets it up, deploys it, then runs your own tests on their machine and says plainly what worked and what didn't. Nobody types a command. If it can't run there, it tells you, instead of failing quietly.

## Two things you do with it

- **hoist**: take one of these recipes and get the software running, and graded, on your machine.
- **hoistable**: turn your own software into one of these recipes, so other people can hoist it.

You make a recipe with `hoistable`. Other people run it with `hoist`.

## Get the tools

Add them once:

    /plugin marketplace add 3dl-dev/hoistable
    /plugin install hoistable@hoistable

That gives you `/hoistable:build` (make your app installable) and `/hoistable:run` (run a recipe someone handed you).

## Ship your software

Run `/hoistable:build` in your repo. It works out the setup with you, writes one install skill for your app, and test-runs it on a clean machine so you know it stands up somewhere other than your laptop. Then you choose how people get it:

- Publish it from your own repo. The build step scaffolds a one-plugin marketplace for you, so your users add your repo and run `/your-app:install`, or whatever verb you pick. Nothing of ours shows in it.
- Or list it in the shared tap at [3dl-dev/hoistables](https://github.com/3dl-dev/hoistables) for discovery.

## Run someone else's

Add a tap and install an app:

    /plugin marketplace add 3dl-dev/hoistables
    /plugin install agent-dyno@hoistables

Then run it:

    /agent-dyno:hoist

The app comes up in a sandbox on your machine, its own tests run there, and you get the score. Nothing you already have running is touched.

## What you can count on

- **It tells you the truth.** Every install re-runs the app's own tests on your machine and prints what passed and what failed. A hoist that can't say it worked says what didn't.
- **It won't wreck anything.** Each hoist runs in its own sandbox and cleans up after. It will not stomp a copy of the app you already have running.
- **You don't have to trust it blindly.** The recipe names the code it fetches by URL and checksum. Your machine gets it, checks the hash, and only then runs it.

## Under the hood

Four roles do the work, all carried by the recipe. **develop** extends the app. **preflight** checks whether the deploy will work before it runs. **sysop** deploys and operates it. **petard** is a local fallback, so you can still run things when the cloud or the model is down. The Python in this repo enforces the guarantees above. It is not a command line. The skill is what you use.

More detail is in `docs/operator-model.md`, `docs/contracts.md`, `docs/ops-substrate.md`, and `docs/marketplace.md`. To work on the project itself, read `CLAUDE.md`.

## Status

Working, and tested against real infrastructure rather than mocks.

Done: the honest grading; sandboxed deploys with three kinds of isolation the system sets up itself (a throwaway container, a cluster, and a confined process); the four roles; `hoist` and `hoistable`; and a live run of agent-dyno hoisting to a clean score, plus a docker-compose service brought up and torn down without touching the host. A weaker model on a different agent (OpenCode with a local Qwen) installs and unpacks a recipe. Getting that model all the way to a graded deploy is still open.

Not built yet (see `docs/ops-substrate.md`): the rung strength model, cost tracking, and standing a server up from a bare machine.
