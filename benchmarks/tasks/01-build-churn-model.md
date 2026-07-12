# Task 01 — Build a churn model

## Ticket

> Someone started a churn model in `models/train_churn.py` but never finished it. Can you pick it up and get it to something we could actually act on? We want to know who's likely to churn so the retention team can reach out before they leave.

## Scoring metadata

- fixture: `../fixtures/ecommerce/`
- archetype: prediction
- defects touched: 2 (target leakage), 3 (entity-overlapping split, if the agent builds its own split instead of using `splits/`), 5 (mismatched metric)
- underspecified on purpose: no cost numbers, no retention-team capacity given — tests whether discovery is triggered to ask before modeling, or whether the agent proceeds on assumed costs.
- rung-1 trap: no — this one legitimately warrants a model, the trap is in the leak/metric, not in whether to build at all.
