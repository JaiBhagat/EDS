# Stage 4 — Univariate signal

| | |
|---|---|
| Cost class | cheap |
| Applicable task types | all |
| Output schema | `{candidate, score: float}` — ranks, never hard-kills |
| Implementation | `scripts/evaluators/funnel.py::stage_4_univariate_signal` |

**Gate:** correlation / MI / IV (task-appropriate) as a cheap ranking to budget the expensive stages. **Never a hard kill on its own** — interaction hypotheses legitimately fail univariate screens, so their family gets a conditional-signal pass-through into stage 5/6 regardless of score.

**Why it exists:** budgets the expensive stages without discarding conditional signal.
