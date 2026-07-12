---
name: mde
description: >
  The Model Discovery Engine — the reasoning loop for modeling: validation
  contract → baseline → diagnosis → candidates → calibration → champion.
  Diagnosis before search (the anti-AutoML core): slice errors before HPO so
  diagnosis earns the right to search. Use whenever modeling work goes beyond
  baseline-first: the baseline is measured, it's not enough, and now the
  question is how to beat it systematically. Trigger on "improve the model",
  "try more approaches", "the baseline isn't good enough", or whenever the
  Plan's model stage is next after baseline. Do NOT use before a baseline
  exists — hand off to `baseline-first`. Do NOT use for threshold/operating-
  point selection — hand off to `decision-optimization`.
argument-hint: "[round|diagnose|champion]"
license: MIT
---

# Model Discovery Engine

The pipeline between "we have a baseline" and "we have a champion ready for
thresholds." Everything here runs under a locked validation contract; every fit
is logged; the confirmation holdout is touched exactly once.

## Prerequisites

Before entering the MDE loop:
1. A confirmed Brief with a Plan (`.eds/BRIEF.md`)
2. Features selected (FDE complete or at least a candidate set identified)
3. A baseline measured (`baseline-first` done) — this is the bar to beat
4. An evaluation contract designed (`evaluation-design` done)

## The MDE loop

### Step 1 — Lock the validation contract

Run `python skills/mde/scripts/validation_contract.py create <data.csv> --target <col> [--time-col <col>] [--entity-col <col>]`.

The contract defines: metric, split strategy, seed, fold count. Once written, its hash locks it — every experiment must reference this hash. A changed contract means all prior experiments are invalidated. Present the contract to the user for sign-off before proceeding.

### Step 2 — Initialize the candidate table

Run `python skills/mde/scripts/candidate_table.py init --task-type <type>`.

The table starts with the standard baselines (majority/mean, linear, GBM-default). The baseline-first results already measured should be logged into the experiment log under this contract hash.

### Step 3 — Run baselines under the contract

Fit each baseline candidate, log results:

```
python skills/mde/scripts/experiment_log.py log \
    --name <name> --model-type <type> \
    --params '{}' --metric-value <val> \
    --contract-hash <hash> --seed 42 \
    --log-path .eds/models/experiment_log.json
```

The best baseline is now the reigning champion. If the baseline already meets the Brief's success bar, **stop here** — the ladder says the simplest thing that works wins. Only proceed if the baseline falls short.

### Step 4 — Diagnosis before search

**This is the anti-AutoML core.** Before trying fancier models, understand WHY the baseline is wrong:

1. Run error analysis: `python skills/error-analysis/scripts/slice_errors.py` on the baseline's predictions
2. Triage: is it data, label, or model? (see `error-analysis` skill)
3. Based on the diagnosis:
   - **Data problem** → back to `data-audit`, not more modeling
   - **Label problem** → back to `label-design`
   - **Feature gap** → emit a feature back-request to `fde` for the specific slice/signal
   - **Model capacity** → add a candidate to the strategy table WITH the diagnosis as rationale

Every candidate added to the table must cite a diagnosis finding. "Let's try XGBoost" is not a rationale. "Error analysis shows high-variance errors concentrated in the new-customer segment — try bagging (RF) to reduce variance" is.

### Step 5 — Run candidates

For each pending candidate in the strategy table:
1. Fit under the same validation contract (same splits, same metric)
2. Log to experiment_log.py with the contract hash
3. Mark the candidate as evaluated in the table

### Step 6 — SE-floor stopping

After each round of candidates, check whether further search is worthwhile:

Run `python skills/mde/scripts/champion_selection.py select` — it computes the SE-floor: if the gap between the top-2 models is less than 0.5×SE of the leader's fold scores, further HPO is unlikely to help. Report the SE-floor finding to the user.

If the SE floor says "stop", proceed to calibration. If it says "room to improve" AND the diagnosis suggests specific candidates, run another round (back to Step 4).

### Step 7 — Calibration

Before any threshold is set, check calibration:

```
python skills/mde/scripts/calibration.py check <predictions.csv> \
    --y-true <col> --y-prob <col>
```

If the verdict is "poorly calibrated" or worse, apply recalibration:

```
python skills/mde/scripts/calibration.py fix <predictions.csv> \
    --y-true <col> --y-prob <col> --method isotonic
```

The calibration report is required evidence for the decision-optimization gate downstream.

### Step 8 — Champion selection

Run `python skills/mde/scripts/champion_selection.py select` to pick the Pareto-optimal champion (maximize metric, minimize complexity — parsimony wins ties).

### Step 9 — Confirmation holdout touch

Touch the confirmation holdout EXACTLY ONCE:

```
python skills/mde/scripts/holdout_ledger.py touch \
    --stage model --score <val> --metric <metric> \
    --model-name <champion-name>
```

The holdout ledger is shared with FDE. A second touch is refused unless explicitly deferred.

### Step 10 — Generate monitoring contract

```
python skills/mde/scripts/champion_selection.py monitoring-contract \
    --champion-path .eds/models/champion.json
```

The champion ships with: input drift (PSI), output drift (KS), performance decay (metric ± 2SE), operational checks (queue size, action rate), and retrain triggers.

## What NOT to do

- **No AutoML.** Never launch a grid search without a diagnosis finding that justifies expanding the search space. The diagnosis earns the right to search.
- **No threshold selection.** Thresholds leave the MDE to `decision-optimization` — they are NEVER chosen on test data.
- **No holdout peeking.** The confirmation holdout is touched once (Step 9), not used for model selection. Fold scores drive selection.
- **No silent contract changes.** Changing the split or metric mid-experiment invalidates all prior results. Write a new contract and re-run.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
