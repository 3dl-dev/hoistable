#!/usr/bin/env python3
"""Assemble an app's Layer 2 recipe into ONE self-contained distributable hoist SKILL.

This is use-case 1 (the skill builder): it takes an app's config (its Layer 2 recipe) and
assembles a single `<app>.hoist.SKILL.md`, the carried recipe wrapped as a *skill* an
agent invokes (agent-first), with the honest-grade discipline stamped in as prose. On
first use the receiver agent follows that recipe **in its own session, with ordinary
tools**: resolve the isolation, clone, deploy in a sandbox, health, held-back acceptance,
tear down, and report an honest transfer score. There is nothing of ours to fetch or run,
no toolchain, no CLI, no shipped runtime. The channel is the skill; the agent does the
work in-context.

This module only *assembles* the file. The judgment, which config, what the acceptance
means, carry vs bind, is the builder skill's (see builder/SKILL.md), not this script's.
Assembly is deterministic (same recipe -> same bytes). Whether even this assembly stays
Python or becomes the build agent's own authoring is an open question (see the reshape
items); it survives here only as build-time convenience, never as anything a receiver runs.

The carried recipe travels inside the file in a fenced ```json block; `extract_config`
recovers it, so the config never lives outside the one file. Standard library only.
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(_HERE, "seed", "hoist-rebuild.md")

CARRIED_HEADER = "## The carried recipe (the authority; everything the hoist needs travels here)"
_FENCE = "```"

# Invariants every emitted skill obeys, independent of the app. Static: they are the
# honest-grade discipline the receiver agent follows, restated as guarantees.
CHECKS = [
    "**Non-destructive.** The deploy lands in an isolated namespace or sandbox (its own "
    "name, ports, storage); a profile that declares no isolation is refused; teardown "
    "always runs and leaves no residue on the host. It never re-runs <app>'s own "
    "singular deployment onto a live host.",
    "**No silent success.** <app> is graded on the real target; a run that cannot say it "
    "worked says what did not transfer. A design never reads as a running system.",
    "**No toolchain, no command line.** You hoist <app> in this session with ordinary "
    "tools; there is nothing of ours to fetch or run. The carried recipe is everything.",
]


def _default_profile(config):
    name = config.get("default_profile") or "default"
    profiles = config.get("profiles") or {}
    return name, (profiles.get(name) or {})


def _binds_section(config, profile):
    lines = []
    for b in config.get("binds") or []:
        req = "required" if b.get("required") else "optional"
        lines.append(f"- `{b['name']}` ({req}), probe: `{b.get('probe', '')}`")
    iso = profile.get("isolation") or {}
    require = iso.get("require")
    if iso.get("none"):
        lines.append("- isolation substrate: none required, this profile is hermetic "
                     f"({iso.get('why', 'declares it touches no shared state')}).")
    elif require and require not in ("host", "namespace", None):
        lines.append(f"- isolation substrate (required): a rung of at least "
                     f"`{require}` strength must resolve on the target, or this is "
                     f"cannot-build.")
    else:
        lines.append("- isolation substrate: the host floor (this profile's own "
                     "declared namespace); no stronger rung required.")
    return "\n".join(lines) or "- (none)"


def _acceptance_section(profile):
    lines = [f"- `{c.get('name', '?')}`: `{c.get('check', '')}`"
             for c in (profile.get("acceptance") or [])]
    return "\n".join(lines) or "- (none declared, the recipe transfers nothing to grade)"


def _default_description(app):
    """The app-first default, carrying none of our naming."""
    return (f"Set up and run {app} on this machine, then self-test it and report "
            f"honestly what worked. It ships as a recipe your agent follows here, in "
            f"this session: it brings {app} up in a sandbox, grades it, and tears it "
            f"down clean.")


def emit_skill(app_dir_or_config, seed_path=SEED, config_name="config.json",
               skill_name=None, description=None):
    """Assemble the self-contained skill text for an app. `app_dir_or_config` is a
    directory holding config.json, or a path to a config file. Deterministic: identical
    inputs -> identical bytes. The emitted skill carries nothing to fetch or run.

    `skill_name` and `description` let the DEVELOPER brand the output as their own
    product. The result is the developer's, not ours: they choose the name their users
    invoke and the words their users read. Defaults carry none of our naming (no
    "hoist", no "hoistable"), so a developer who does nothing still ships something
    app-first, with us invisible. Our own conventions (e.g. a `hoist` skill name in our
    tap) are just callers passing those values in."""
    path = app_dir_or_config
    if os.path.isdir(path):
        path = os.path.join(path, config_name)
    with open(path) as f:
        config = json.load(f)
    # The emitted skill is self-contained prose: no toolchain pin, nothing of ours to
    # fetch or run. The receiver agent does the hoist in its own session.
    app = config.get("app", "app")
    _, profile = _default_profile(config)
    skill_name = skill_name or "deploy"                 # the dev's verb; never forced to ours
    description = description or _default_description(app)

    with open(seed_path) as f:
        stamped = f.read().strip().replace("<app>", app).replace("<verb>", skill_name)

    carried = json.dumps(config, indent=2, sort_keys=True)
    checks = "\n".join(f"- {c.replace('<app>', app)}" for c in CHECKS)

    parts = [
        "---",
        f"name: {skill_name}",
        # quote the description so any colon in it is YAML-safe (an unquoted ": " breaks
        # the frontmatter and the skill silently fails to load); json.dumps is valid YAML.
        f"description: {json.dumps(description)}",
        "---",
        "",
        stamped,
        "",
        CARRIED_HEADER,
        "",
        f"{_FENCE}json",
        carried,
        _FENCE,
        "",
        "## Binds (resolve these on the target; a missing required one is cannot-build)",
        "",
        _binds_section(config, profile),
        "",
        "## Checks (invariants every deploy obeys)",
        "",
        checks,
        "",
        "## Acceptance (the held-back transfer test; the honest score)",
        "",
        _acceptance_section(profile),
        "",
    ]
    return "\n".join(parts)


def scaffold_marketplace(out_dir, app_config, *, marketplace_name, owner=None,
                         plugin_name=None, skill_name=None, description=None,
                         config_name="config.json"):
    """Write a ready-to-push, single-plugin marketplace so a developer can self-host
    their app's install skill from their own repo, branded entirely as theirs. Writes:

        out_dir/.claude-plugin/marketplace.json
        out_dir/plugins/<plugin>/.claude-plugin/plugin.json
        out_dir/plugins/<plugin>/skills/<skill>/SKILL.md

    Their users then run `/plugin marketplace add <their-repo>` and invoke
    `/<plugin>:<skill>`. Nothing of ours appears in it: plugin, skill, and description
    all default app-first and are theirs to set. Returns the `/<plugin>:<skill>`
    invocation string their users will type."""
    cfg = app_config if not os.path.isdir(app_config) else os.path.join(app_config, config_name)
    app = json.load(open(cfg)).get("app", "app")
    plugin_name = plugin_name or app
    skill_name = skill_name or "deploy"
    description = description or _default_description(app)
    text = emit_skill(app_config, skill_name=skill_name, description=description,
                     config_name=config_name)
    pdir = os.path.join(out_dir, "plugins", plugin_name)
    os.makedirs(os.path.join(pdir, "skills", skill_name), exist_ok=True)
    os.makedirs(os.path.join(pdir, ".claude-plugin"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, ".claude-plugin"), exist_ok=True)
    with open(os.path.join(pdir, "skills", skill_name, "SKILL.md"), "w") as f:
        f.write(text)
    with open(os.path.join(pdir, ".claude-plugin", "plugin.json"), "w") as f:
        json.dump({"name": plugin_name, "description": description}, f, indent=2)
    market = {"name": marketplace_name, "description": f"Install and run {app}.",
              "plugins": [{"name": plugin_name, "source": f"./plugins/{plugin_name}",
                          "description": description, "version": "0.1.0"}]}
    if owner:
        market["owner"] = owner
    with open(os.path.join(out_dir, ".claude-plugin", "marketplace.json"), "w") as f:
        json.dump(market, f, indent=2)
    return f"/{plugin_name}:{skill_name}"


def extract_config(skill_text):
    """Recover the carried recipe from an emitted skill: the self-extracting step. Finds
    the first fenced json block under the carried-recipe header and parses it. Raises if
    the file carries no recoverable recipe."""
    idx = skill_text.find(CARRIED_HEADER)
    if idx < 0:
        raise ValueError("no carried recipe: not a hoist skill emitted by this builder")
    rest = skill_text[idx:]
    open_fence = rest.find(_FENCE + "json")
    if open_fence < 0:
        raise ValueError("carried recipe fence not found")
    body_start = rest.find("\n", open_fence) + 1
    close_fence = rest.find("\n" + _FENCE, body_start)
    if close_fence < 0:
        raise ValueError("carried recipe fence not closed")
    return json.loads(rest[body_start:close_fence])


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="assemble an app's Layer 2 recipe as a self-contained hoist SKILL")
    ap.add_argument("app_dir", help="dir with config.json (or a config.json path)")
    ap.add_argument("--out", default=None, help="output path (default: <app>.hoist.SKILL.md)")
    args = ap.parse_args(argv)
    text = emit_skill(args.app_dir)
    cfg = extract_config(text)
    out = args.out or f"{cfg.get('app', 'app')}.hoist.SKILL.md"
    with open(out, "w") as f:
        f.write(text)
    print(f"assembled {out} ({len(text)} bytes, self-contained)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
