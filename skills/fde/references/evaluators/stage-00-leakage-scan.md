# Stage 0 — Leakage scan

| | |
|---|---|
| Cost class | cheap |
| Applicable task types | classification, regression, ranking, forecasting |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_0_leakage_scan` |

**Gate:** target-derivation trace (name-pattern match against post-outcome vocabulary), availability-timeline check, suspiciously-perfect correlation with target.

**Why it exists:** never-cut. Runs first because a leaky feature poisons every downstream ranking — SHAP will *love* leakage. Not removable by any domain pack.
