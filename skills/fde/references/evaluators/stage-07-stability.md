# Stage 7 — Stability

| | |
|---|---|
| Cost class | expensive |
| Applicable task types | classification, regression, forecasting |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_7_stability` |

**Gate:** importance/signal rank across time slices; a candidate whose rank swings past a stated drift threshold is evicted.

**Why it exists:** a feature that ranks #3 in March and #300 in June is a production incident on a delay, not a shipped feature.
