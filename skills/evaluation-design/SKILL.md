---
name: evaluation-design
description: >
  Designs how a model or analysis gets judged — axiom 3 (baseline is the
  burden of proof) and axiom 6 (models serve operational decisions, not
  metrics). Picks a metric matched to cost asymmetry and operational
  capacity, mandates an out-of-time split, checks performance holds across
  segments, and statistically compares against baseline before declaring a
  win. Use this whenever a metric is being chosen, a train/test split is
  being designed, a model's results are being reported as "good", or someone
  asks "is this good enough to ship". Also trigger on any test-set-reuse
  ("let's just check it again on the test set") request. Do NOT use for
  early EDA with no candidate model yet — hand off to `eda-workflow`; or for
  leakage mechanics themselves — hand off to `leakage-check`.
argument-hint: "[metric|split-plan|results-to-judge]"
license: MIT
---

# Evaluation design

Never-cut item 3, operationalized. If `.eds/BRIEF.md` exists, its "Success metric & baseline bar" and "Operational constraints & consumption path" sections already answer most of check 1 below — read them before picking a metric from scratch.

## The four checks, in order

### 1. Metric matched to cost asymmetry AND operational capacity

Accuracy is almost never the right metric. Ask: what does a false positive cost, what does a false negative cost, and are those costs even close to equal? Then ask the operational question the metric alone can't answer: at the operating point this metric implies, does the *volume* of flagged cases fit the reviewer/channel capacity stated in the Brief? A recall improvement that triples the review queue past its capacity is a regression, not a win (A6) — report both the metric and the resulting operational load in the same breath.

If the Brief doesn't state a cost asymmetry or capacity number, that's a gap — ask the user, don't default to accuracy/F1 because it's convenient.

### 2. Split design — out-of-time, not just held-out

Delegate the mechanics to `leakage-check` (entity overlap, time-based split) — don't re-derive that here. This check is the evaluation-design half: confirm the split actually answers the deployment question. If the model will score future, unseen time periods, the evaluation split must be a later time window, full stop. A random same-window holdout only tells you about interpolation, not the production task.

### 3. Segment stability

An aggregate metric can hide a model that's great on the majority segment and useless (or harmful) on a minority one that matters operationally. Slice the held-out evaluation by the segments the Brief or domain knowledge flags as consequential (e.g. new vs. existing customers, by region, by time-of-day) and check the metric doesn't collapse on any slice big enough to matter. Don't slice everything — pick segments with a stated reason, not a fishing expedition.

### 4. Statistical comparison to baseline

"Better" needs a confidence statement, not a point estimate. Run `skills/evaluation-design/scripts/baseline_compare.py <path.csv> --y-true <col> --y-baseline <col> --y-model <col> [--metric auto|auc|accuracy|mae|rmse]` — it bootstraps the metric difference and reports whether the model's improvement survives resampling noise. A win inside the bootstrap interval around zero is not a win; report it as "no significant difference from baseline" rather than picking the higher point estimate.

## Test-set reuse — hard stop

Once a test/holdout set has been used to pick a metric value that informed a decision (model choice, threshold, "ship it"), it is spent. Looking at it again to check a tweak is test-set leakage through repetition, not a mechanic leak, but it corrupts the same honesty this whole skill exists to protect. If a re-check is genuinely needed, that means either draw a fresh out-of-time slice, or say explicitly that the reported number is now optimistic — never re-run silently and report the new number as if it were the first look.

## Output

State the decision the metric serves, the metric plus its cost/capacity fit, the split type, and the baseline comparison result — in that order, not a metrics table with no framing:

```
## Evaluation: <what's being judged>
- decision served: <one line>
- metric: <name> — matched to <cost asymmetry / capacity constraint>
- split: <type>, <window if OOT>
- segment check: <pass/fail + which segment if fail>
- vs. baseline: <result from baseline_compare.py, with CI>
```

If any check can't be completed (no cost numbers, no segment labels available), mark it: `# eds: deferred — <reason>` and say what's now unverified because of the gap.

## Emit the contract

The metric and split decided here are not just prose — write them to a machine-readable
contract so every downstream stage (baseline, FDE, MDE) reads the same value instead of
re-deriving it:

    python skills/mde/scripts/validation_contract.py create <data.csv> \
        --target <col> [--time-col <col>] [--entity-col <col>]

The contract reads `.eds/BRIEF.md`'s primary metric automatically. Present the resulting
contract (metric, split strategy, seed, hash) for user sign-off — this is the `user-signoff`
gate on this stage. Once locked, MDE Step 1 *verifies* this contract rather than creating
a new one; a changed contract invalidates all prior experiments.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
