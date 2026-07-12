# Stage 3 — Cardinality & encodability

| | |
|---|---|
| Cost class | cheap |
| Applicable task types | all (categorical features only) |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_3_cardinality` |

**Gate:** category count above a stated ceiling is evicted (or routed back to Engineer for a hashing/target-encoding recipe rather than raw one-hot).

**Why it exists:** explosive cardinality is a cost and overfitting hazard, caught before the expensive model-based stages waste budget on it.
