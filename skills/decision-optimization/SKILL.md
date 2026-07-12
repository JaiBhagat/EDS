---
name: decision-optimization
description: >
  Turns a score into an action — axiom 6 operationalized. Sets thresholds
  by expected value and operational capacity (not by eyeballing an ROC
  curve), maps scores to actions, and designs the human-in-the-loop point
  where one exists. Use this whenever a model's output (score/probability)
  needs to become a decision: approve/deny, flag/don't-flag, route-to-review,
  a ranked queue with a cutoff. Also trigger on "what threshold should we
  use", "how many should we flag", or a review queue sized against model
  output. Do NOT use for metric selection itself (that's `evaluation-design`)
  or for building the score in the first place (that's `baseline-first` /
  custom modeling) — this skill starts once a score already exists.
argument-hint: "[score-column|cost-matrix|capacity]"
license: MIT
---

# Decision optimization

If `.eds/BRIEF.md` exists, its "Operational constraints & consumption path" section already states who consumes the decision and at what capacity — use those numbers, don't ask for them again if they're already recorded.

## The three checks, in order

### 1. Threshold set by expected value AND capacity, not by metric alone

A threshold chosen to maximize F1 or "look good on the ROC curve" ignores what happens downstream. Two numbers are required before a threshold is defensible: the cost matrix (value of a true positive, cost of a false positive, cost of a false negative, value of a true negative — even rough order-of-magnitude estimates count) and the operational capacity that consumes the flagged cases (queue size, reviewer-hours, channel throughput). Run `skills/decision-optimization/scripts/threshold_ev.py <path.csv> --score-col <col> --y-true <col> --cost-matrix tp=<v>,fp=<v>,fn=<v>,tn=<v> [--capacity <n>]` — it sweeps thresholds, reports the EV-optimal one, and separately reports the highest threshold that keeps the flagged volume within stated capacity. If those two thresholds disagree, that disagreement *is* the finding — report both, don't silently pick one.

### 2. Score-to-action mapping

State explicitly what happens at each band of the score, not just where the cutoff sits. A single threshold often hides that the top decile should get one action (auto-decline) and a middle band another (route to review) rather than one binary split. If the Brief's consumption path implies more than two actions, the threshold analysis should reflect that instead of forcing a binary cut where none is warranted.

### 3. Human-in-the-loop design

If a human reviews any band of scores before an action is taken, state what information they see (the score alone is usually not enough — the features that drove it, comparable past cases), what their override rate is expected/observed to be, and what happens if they disagree with the model systematically in one direction (that's signal the model or threshold is miscalibrated for this segment, not noise to average away).

## Output

```
## Decision optimization: <score> -> <action>
- cost matrix: tp=<v> fp=<v> fn=<v> tn=<v>
- EV-optimal threshold: <t> (expected value: <ev>)
- capacity-constrained threshold: <t'> (flags <n>/<capacity>)
- action mapping: <bands -> actions>
- human-in-the-loop: <what reviewer sees, override handling, or "fully automated">
```

If the cost matrix can't be estimated even roughly, that's a gap to close with the user (ask), not a default of equal costs — equal costs is itself a strong, usually wrong, assumption. If genuinely unresolvable now: `# eds: deferred — no cost-matrix estimate, threshold set by <fallback>, revisit`.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
