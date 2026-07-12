# Fixture: ecommerce

Synthetic e-commerce analytics repo used as the starting point for benchmark tickets in `../../tasks/`. Regenerate with `python generate.py` (seeded, deterministic).

## Layout

- `data/users.csv` — user_id, signup_date, region, plan, churned (target)
- `data/orders.csv` — order-level transactions
- `data/events.csv` — login/view/cart/support-ticket event log
- `data/features.csv` — a candidate feature table (`account_closed_reason`)
- `splits/train.csv`, `splits/test.csv` — a pre-made user-level train/test split
- `models/train_churn.py` — a WIP churn model someone on the team started
- `notebooks/eda.ipynb` — basic exploration
- `notebooks/model_dev.ipynb` — a WIP order-value model, cross-validated

This fixture is used as-is by benchmark tickets — do not "fix" it directly; the defects are the point. See `../tasks/_answer-key.md` for what's actually planted (scoring reference, not meant to be read before running a ticket against this fixture).
