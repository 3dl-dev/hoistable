<!-- target: model=qwen3.8-27b agent=opencode reference=claude -->

# Target profile: qwen-opencode

OpenCode driving Qwen3.8-27B, a weaker receiver than the reference (claude). The corrections
below are **measured** (grounding runs produced each; see where noted), and they are about how
this model tends to mis-follow *any* skill, not about a particular skill's content. When a
skill is cross-compiled for this target, its variant stamps this delta. Unmeasured buckets
stay empty: no invented fixes.

## Corrections (measured)

**1. A failing check is honest-failure. Never argue past it.** Measured: given a skill whose
check genuinely failed, this model relabeled the outcome "done" on its own judgment that the
result "looked right", and left the non-compliant result standing. Hold the line: the check
result is the authority. One failing check means honest-failure, full stop. Do not relabel it,
do not substitute your impression that it looks fine, do not present a result that failed a
check as a success. If you believe the check itself is wrong, say so as a finding, but still
report honest-failure.

**2. Resolve what you need with the plainest probes; do not characterize the environment
beyond what the recipe asks.** Measured: resolving its setup, this model reached for broad
environment probes (reading system files under `/proc`, `/etc`, `/dev`; scanning for tools the
recipe never named) that trip the agent's permission gate and, with no human to approve,
silently abort the whole run. Use only the plain commands the recipe calls for. Do not read
system files or scan for capabilities the recipe did not ask about; the recipe already names
what you need.

## Buckets not yet measured
- Ambiguity resolved the wrong way: none recorded.
- Missing or underspecified step skipped: none recorded.
- Agent skill-loading friction: none recorded.
