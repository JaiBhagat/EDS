# Stage 6 — Model-based importance

| | |
|---|---|
| Cost class | expensive |
| Applicable task types | classification, regression |
| Output schema | `{candidate, importance: float}` — ranks, stage 7 decides eviction |
| Implementation | `scripts/evaluators/funnel.py::stage_6_model_importance` |

**Gate:** SHAP/permutation/feature_importances_ on a fast reference model, run on a **rotating evaluation fold**, never the confirmation holdout (F7).

**Why it exists:** the expensive gate — only reached by stage-5 survivors, so it never wastes budget ranking redundant or degenerate columns.
