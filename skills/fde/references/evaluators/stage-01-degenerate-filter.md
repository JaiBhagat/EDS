# Stage 1 — Degenerate filter

| | |
|---|---|
| Cost class | free |
| Applicable task types | all |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_1_degenerate_filter` |

**Gate:** constants/near-constants (single value ≥ threshold share of rows), duplicates (identical value hash vs. an already-kept candidate).

**Why it exists:** free to compute; removing degenerate columns makes every later stage cheaper and every ranking honest.
