#!/bin/bash
# claude-hook: event=SessionStart matcher=startup|resume|compact timeout=10 order=20
# Continuity shim: re-inject Hoistable's OPERATING POSTURE on session start and,
# crucially, after compaction. The existing global spine (precompact.sh +
# session-start.sh) preserves the WORK pointer (which item, which step, next
# action). It does not preserve the SHAPE -- how to think -- so compaction can
# summarize CLAUDE.md away and the agent resumes doing the right work in the wrong
# shape, needing re-steering. This holds the shape. Echo-only; no side effects.
set -euo pipefail

# Only inject inside this repo (portable: works for anyone who clones it).
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || echo)}"
[ -n "$ROOT" ] && [ -f "$ROOT/CLAUDE.md" ] || exit 0
grep -q "Hoistable (project standing orders)" "$ROOT/CLAUDE.md" 2>/dev/null || exit 0

read -r -d '' POSTURE <<'EOF' || true
## Hoistable operating posture (hold this through compaction; full text in CLAUDE.md)

Compaction may have summarized CLAUDE.md away. The SHAPE is fundamental, not stylistic.

FIRST, the one that keeps drifting after a reset: WE DISTRIBUTE A *SKILL*, NOT CODE. The
skill does the work in the RECEIVER's session; iterating that skill until it is grounded,
correct, and accurate is the job, and you own it. Code exists only to optimize
deterministic operations invariant across the solution space (arithmetic, checksums, the
enforced order). Code NEVER accomplishes the task. Writing software to do the work instead
of a skill that has the receiver's agent do the work = you have left the product.

Then the rest of the shape:

- You ARE the operator. develop/preflight/sysop/petard are agent roles, not programs.
  The loop is a skill you RUN, not a script to build -- "manual" and "automated" are
  the same act.
- Resolve, don't depend. Author a missing rung/adapter/profile just-in-time when a
  problem needs it; any ladder/registry is a CACHE, not a menu. Interrogate the target
  in the loop; do not pre-mint every contingency into code.
- Anti-constrain (don't box in what needn't be). Re-derive, don't freeze. Grade against
  real infrastructure, never a mock of the thing under test.
- Honest, always: separate built-AND-tested from designed, out loud; no silent success,
  no silent spend.

Catch yourself:
- pre-building a backend / rung / menu -> resolve it, or author it just-in-time.
- writing a script to "automate the loop" -> you ARE the loop; it lives in a skill.
- "here's what now runs" sounding broader than what is built+tested -> say built-vs-designed.
- reaching for rd (or our tooling) as part of the product -> ours, not Hoistable's.
- labeling a rung/result with a strength it didn't earn -> grade it, label what you measured.
EOF

ESCAPED=$(printf '%s' "$POSTURE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": $ESCAPED
  }
}
JSON
