# Forecasting archetype bank

For time-series/aggregate-future-value problems: demand, revenue, traffic, staffing. Ask after the universal bank, pruned by its answers.

1. **Granularity** — What's the forecast unit and cadence (daily SKU-level, weekly regional, monthly total)?
2. **Horizon vs. history** — How far ahead must it forecast, and how much history exists? (A 12-month-ahead forecast on 8 months of history is a different problem than "not enough data" stated plainly.)
3. **Seasonality & events** — Known seasonal patterns, holidays, promotions, or one-off events (COVID, a price change) that break the series?
4. **Hierarchy** — Does this need to reconcile across a hierarchy (SKU → category → total; store → region → company)? Do the pieces need to sum to the total?
5. **Exogenous drivers** — Are there known future inputs that affect the target (planned promotions, price changes, headcount plans, weather)? Are those inputs known in advance or only after the fact?
6. **Update cadence** — Is this forecast made once, or re-run and re-evaluated on a rolling basis? What triggers a re-forecast?
7. **Error tolerance** — Is over-forecasting or under-forecasting worse (overstaffing cost vs. understaffing cost, overstock vs. stockout)?
8. **Current process** — Is there an existing forecast (naive, last-year-same-period, an analyst's spreadsheet)? That's the burden-of-proof baseline — get its actual accuracy, not an assumption.
9. **Structural breaks** — Any known upcoming change that invalidates historical patterns (new product line, market exit, policy change)?

## Routing

- Q1–Q2 feed the `time_coverage.py` probe and the FRAMING stage's observation/performance window structure directly.
- Q4 (hierarchy/reconciliation) is a scope decision — surface it before framing, it changes the whole modeling approach, not just a feature.
- Q7/Q9 feed `evaluation-design` (asymmetric loss) and `model-monitoring` (structural-break triggers) respectively — capture verbatim.
- Never let shuffled CV or random-split evaluation happen on this archetype — leakage-check's time-shuffle warning applies by default.
