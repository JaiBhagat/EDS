# Stage 9 — Serving review

| | |
|---|---|
| Cost class | moderate — needs per-feature cost/availability metadata |
| Applicable task types | all, mandatory for production deployment |
| Output schema | `{candidate, passed: bool, reason}` |
| Implementation | `scripts/evaluators/funnel.py::stage_9_serving_review` |

**Gate:** inference cost vs. budget, online availability, training-serving parity. Run last because it needs the near-final set to price realistically; extended by the `feature-lifecycle` pack when installed.

**Why it exists:** F6 — a feature set the operation can't run in production is a failed feature set, however good its offline score.
