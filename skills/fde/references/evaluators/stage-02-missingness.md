# Stage 2 — Missingness & coverage

| | |
|---|---|
| Cost class | free |
| Applicable task types | all |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_2_missingness` |

**Gate:** fraction missing at or above a stated threshold is evicted; structural missingness that might itself be signal is flagged, not silently imputed away.

**Why it exists:** a feature absent for most of the population can't drive the decision (A6).
