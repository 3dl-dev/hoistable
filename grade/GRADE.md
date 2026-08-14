# The grade (the loss function)

The objective is not the `.py` suite. It is the ouroboros: a fresh agent, given only an
emitted skill, self-extracts the harness, hoists the app on a real target in a real
session, and grades it. The honest transfer over that whole tower is the loss.

Run it:

    Workflow({ scriptPath: "grade/ouroboros.js" })                          # agent-dyno, honcho, hoistable
    Workflow({ scriptPath: "grade/ouroboros.js", args: { apps: ["agent-dyno"] } })

It emits each app's skill, then dispatches a receiver agent with **no repo access** to
install and grade it, exactly as a stranger would. PASS means every app built and its
acceptance transferred on a real target. That is the release gate: cut a release only when
this passes.

The `.py` tests (`tests/test_*.py`) check the neutral core's mechanics only. A green suite
with a failing or unrun ouroboros grade is the altitude confound. Green checkmarks on our
code are not the product working. This grade outranks the suite.
