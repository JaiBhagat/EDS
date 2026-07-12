# Universal question bank

Ask these of every problem, regardless of archetype. Deliver in batches of 2–4 per turn, never as a single long form. Skip any question the data can answer instead — run the probe, don't ask.

1. **Decision** — What decision changes based on this analysis's output? Who makes it?
2. **Action** — What action follows from a given answer/prediction? Is there a defined action for every plausible output value?
3. **Cost asymmetry** — What does it cost to be wrong in each direction (false positive vs. false negative, overestimate vs. underestimate)?
4. **Population** — Who/what is this about? Any known exclusions or edge segments that behave differently?
5. **Cadence** — How often does this decision get made — once, daily, real-time, per event?
6. **Horizon** — How far ahead does the answer need to hold (a prediction for tomorrow vs. next quarter)?
7. **Success metric** — If this works, what number moves, and how would you know it wasn't chance?
8. **Constraints** — Compute, latency, explainability, regulatory, or team constraints that bound the solution?
9. **Prior attempts** — Has this been tried before? What existed already — a dashboard, a rule, a prior model? Why isn't it enough?
10. **Deadline** — Is there a date this needs to inform, or is this open-ended exploration?

## Archetype classification

Classify during Stage 1–2 from the problem statement and Q1/Q2 answers, then pull the matching archetype bank instead of asking all banks:

- **Prediction** (per-entity outcome, e.g. churn/fraud/default) → `prediction.md`
- **Forecasting** (time series, aggregate future values) → `forecasting.md`
- **Segmentation** (grouping/clustering, no single target) → not yet in core; fall back to universal + `data-audit`.
- **Causal / measurement** ("did X cause Y", "is it worth launching") → `measurement.md`
- **Anomaly** (what's unusual) → not yet in core; fall back to universal + `prediction.md`'s label-strategy questions.
- **Ranking / recommendation** (order or select from a set) → not yet in core; fall back to universal.

Answers prune downstream questions — e.g. a "once, exploratory" cadence answer skips the archetype bank's monitoring/retraining questions entirely.
