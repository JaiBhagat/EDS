# Stage 10 — Final selection + pre-registered confirmation

| | |
|---|---|
| Cost class | expensive, metered — touches the confirmation holdout |
| Applicable task types | classification, regression |
| Output schema | `{selected_set: [candidate], confirmation_score: float}` |
| Implementation | `scripts/evaluators/funnel.py::stage_10_confirmation` |

**Gate:** the chosen set is trained on non-holdout data and evaluated **exactly once** on the untouched confirmation holdout. A second touch requires an explicit `# eds: deferred — holdout re-use` marker; the function itself refuses a silent second call.

**Why it exists:** F7 — the evaluation data is a budget, not a well. This is the number that ships; it must be honest.
