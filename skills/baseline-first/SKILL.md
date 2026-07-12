---
name: baseline-first
description: >
  Forces ladder rungs 5-6 before rung 8 — axiom 3, the baseline is the
  burden of proof. Ships the simplest thing that could plausibly work
  (heuristic, then a standard baseline model) and declares the exact bar a
  more complex model must beat, before any custom modeling starts. Use this
  whenever someone is about to reach for a custom/complex model (gradient
  boosting with tuning, a neural net, an ensemble) and no baseline has been
  measured yet, or when asked "should we build a custom model for this".
  Also trigger on "what's the simplest thing that could work". Do NOT use
  once a baseline is already measured and the question is now about
  improving on it — hand off to `fde` (feature search) or `evaluation-design`
  (metric/comparison discipline); that's ordinary modeling work, not this
  skill's job.
argument-hint: "[problem-type|target-col]"
license: MIT
---

# Baseline first

Never-cut item 3's other half (evaluation-design proves the comparison is honest; this skill makes sure there's something honest to compare against). If `.eds/BRIEF.md` exists, its "Success metric & baseline bar" section may already name the bar — check there before picking one from scratch, and update it once measured.

## The two rungs, in order

### Rung 5 — heuristic

Before any model, is there a rule that plausibly captures most of the signal? A threshold on one feature, a lookup table, "flag anything over $X", "predict the same value as last period". If domain knowledge suggests one, state it and measure it — don't skip straight past it because it feels too simple to be worth measuring. A heuristic that gets 80% of the way there for near-zero cost changes the entire cost/benefit case for anything fancier.

### Rung 6 — standard baseline model

Run `skills/baseline-first/scripts/baselines.py <path.csv> --target <col> --split-date-col <col-if-time-based> [--split-frac 0.2]` — it fits and reports a small fixed set of standard baselines appropriate to the task (classification: majority-class, logistic regression; regression: mean-predictor, last-value if a natural ordering/time column exists; a default-hyperparameter GBM in both cases as the "still-simple-but-a-real-model" upper baseline). It respects a time-based split if a date column is given (never a random split when time plausibly matters — see `leakage-check`).

## Declaring the bar

Whichever of the above scores best becomes *the bar*. State it explicitly, in the same units the final evaluation will use: "a custom model must beat AUC 0.71 (logistic baseline) by a margin large enough to survive `evaluation-design`'s bootstrap comparison, not just a higher point estimate." Anything built after this point that doesn't clear the bar isn't shipped, no matter how sophisticated the method.

**If the baseline meets the Brief's success bar:** stop. The ladder says the simplest thing that works wins — a rung-6 victory is a success, not a shortcut. **If it falls short:** log the baseline results into `.eds/models/experiment_log.json` and hand off to `mde` for the diagnosis→candidate→champion loop.

## Output

```
## Baseline: <target>
- heuristic tried: <rule> — <metric>, or "none plausible: <why>"
- majority/mean baseline: <metric>
- logistic/GBM baseline: <metric>
- bar to beat: <metric value>, set by <which baseline>
```

If no heuristic was plausible, say why in one line rather than omitting the row silently — "none plausible" is itself information (it means the problem likely needs real modeling, which is worth stating up front).

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
