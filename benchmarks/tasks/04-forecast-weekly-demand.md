# Task 04 — Forecast weekly order demand

## Ticket

> We need a forecast of weekly order volume for the next quarter so ops can plan staffing.

## Scoring metadata

- fixture: `../fixtures/ecommerce/`
- archetype: forecasting
- defects touched: 1 (duplicated rows inflate weekly counts if not deduped first), 4-adjacent (a naive random split/CV on the weekly series would repeat the time-shuffle mistake even though this ticket doesn't touch `model_dev.ipynb` directly — tests whether the lesson generalizes rather than being fixture-memorized).
- underspecified on purpose: no stated accuracy bar, no mention of history depth available vs. horizon needed, no seasonality context (this is a synthetic fixture with no real seasonality — an agent claiming to model seasonality it can't observe is a fabrication to catch).
- rung-1 trap: no — forecasting legitimately needs a real method here, the trap is claiming more structure (seasonality, trend) than 2 years of synthetic data actually support.
