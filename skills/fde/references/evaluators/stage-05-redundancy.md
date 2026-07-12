# Stage 5 — Redundancy

| | |
|---|---|
| Cost class | moderate |
| Applicable task types | all (numeric features) |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_5_redundancy` |

**Gate:** correlation clustering — keep one representative per cluster, chosen by availability + cost, not by signal alone.

**Why it exists:** multicollinearity destroys explainability and stability; a redundant feature is pure cost.
