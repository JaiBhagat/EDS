# Answer key — planted defects in `../fixtures/ecommerce/`

Scoring reference only. Do not hand this to an arm under test.

1. **Duplicated rows** — `data/orders.csv` has ~2% of rows exactly duplicated on `order_id` (216 rows at generation seed 7). A correct grain/dedup check on `order_id` catches this. Maps to never-cut item 1.

2. **Target leakage** — `data/features.csv`'s `account_closed_reason` is populated if-and-only-if `users.churned == 1` (100%/0% split by construction in `generate.py`). Any model using it will look near-perfect (`models/train_churn.py` reports `accuracy: 1.0` at seed 7) — that suspiciously high number is the intended tell. Maps to never-cut item 2 / axiom 4.

3. **Entity-overlapping split** — `splits/train.csv` and `splits/test.csv` share ~10% of `user_id`s by construction. A correct entity-overlap scan (`split_overlap.py`) catches this immediately. Maps to never-cut item 2.

4. **Time-shuffled CV** — `notebooks/model_dev.ipynb` cross-validates with `KFold(shuffle=True)` on order-level data where `order_date`/`tenure_days` matter — folds mix future and past. Correct catch: this should be a time-respecting split (`TimeSeriesSplit` or an explicit time-based fold), not a random `KFold`. Maps to never-cut item 2 / axiom 4.

5. **Metric mismatched to the decision** — `models/train_churn.py` reports bare accuracy on a ~19% churn base rate with no baseline stated and no cost asymmetry considered (churn intervention: missing a churner is far more expensive than an unnecessary outreach). Even setting aside defect 2's leak, accuracy alone is the wrong metric here. Correct catch: propose a cost-weighted metric (or at minimum recall/precision framed against the intervention capacity) and state the majority-class baseline for comparison. Maps to never-cut item 3 / axiom 6.

## Scoring

Per task, per arm: for each defect the task's fixture surface touches, did the session's final diff/report (a) detect it, (b) fix or explicitly flag it, (c) neither? Pitfall catch rate = (a or b) / defects touched. See `../../EDS-build-plan.md` §9 for the full metric set (LOC, tokens/cost/time, ladder adherence, discovery quality).
