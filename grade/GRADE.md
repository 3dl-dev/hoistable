# The grade (the loss function)

The objective is not any code-mechanics check. It is the ouroboros: a fresh agent, given
**only** a self-contained hoist skill, follows it in its own session and hoists the app on
a real target, then grades it. The honest transfer over that whole run is the loss.

The emitted skill carries the recipe and the honest-grade discipline as prose. It pins **no
toolchain** and carries **nothing to fetch or run**, there is no runtime of ours. So the
receiver agent does the work itself, in context, with ordinary tools (git, the container
runtime, a shell), exactly as a stranger's agent would. "We are just running our local
code" is the confound this exists to kill: the product is an agent following a skill, never
our Python executing.

Run it:

    Workflow({ scriptPath: "grade/ouroboros.js" })                          # agent-dyno, honcho, hoistable
    Workflow({ scriptPath: "grade/ouroboros.js", args: { apps: ["honcho"] } })

It assembles each app's self-contained skill, then dispatches a receiver agent with **no
repo access of ours and nothing to fetch**, which installs and follows the skill exactly as
a stranger would. PASS means every app built and its acceptance transferred on a real target
by an agent following the skill alone. That is the release gate: ship only when this passes.

The remaining `.py` test (`tests/test_builder.py`) checks the emit ASSEMBLY only, that the
one file is well-formed and self-contained (no toolchain leaked in). It is a build
convenience, not the product. A green assembly check with a failing or unrun ouroboros grade
is the altitude confound. Green checkmarks on our code are not the product working. This
grade outranks the assembly check.
