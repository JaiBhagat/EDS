---
description: Review the current diff/notebook for rigor gaps and over-build, using the ds-code-reviewer agent.
argument-hint: "[path]"
---

# /eds-review

Delegate to the `ds-code-reviewer` agent (falling back to inline review against `EDS.md`'s ladder and never-cut list if the agent is unavailable).

Scope: the current diff, or the path given as an argument.

Return two lists, in this order:

1. **Delete-list** — over-engineering: rungs skipped downward (custom code where a library/baseline/heuristic would meet the bar), unrequested abstractions, speculative flexibility.
2. **Add-list** — rigor gaps: never-cut items missing (no grain assertion on a join, no OOT holdout, no seed, PII in output, etc.), each mapped to the axiom or never-cut item it violates.

If touching model-related code, in `ultra` mode also invoke `leakage-hunter` and `stats-skeptic` for adversarial passes and fold their findings into the add-list. One line per finding: location, the gap or excess, the fix.
