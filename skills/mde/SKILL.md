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

Verify the contract created by `evaluation-design` still exists and its hash is unchanged:

    python skills/mde/scripts/validation_contract.py verify .eds/models/validation_contract.json

Only create a new contract if `evaluation-design` was skipped (e.g. when entering MDE directly):

    python skills/mde/scripts/validation_contract.py create <data.csv> --target <col> [--time-col <col>] [--entity-col <col>]

The contract defines: metric, split strategy, seed, fold count. Once written, its hash locks it — every experiment must reference this hash. A changed contract means all prior experiments are invalidated. Present the contract to the user for sign-off before proceeding.

For classification with a calibration need, the split is three-way: train / calibration / test. Carve the calibration slice from the train side (last 10–15% by time), never from test. Record the boundaries in the contract.

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

When comparing the champion against the bar, use the paired bootstrap comparison mode:

    python scripts/lib/bootstrap_ci.py <predictions.csv> \
        --y-true <col> --y-prob <col> --y-prob-baseline <baseline_col> \
        --metric <metric>

### Step 7 — Calibration

Calibration needs a fit set that is **neither train nor test**. If the split in Step 1 didn't
carve one, do it now: take the last 10–15% of *train* (by time, for temporal splits) as the
calibration slice. Never fit a calibrator on the test set — that is the calibration-leakage
failure this interface exists to prevent.

Check calibration on the test predictions:

    python skills/mde/scripts/calibration.py check <test_predictions.csv> \
        --y-true <col> --y-prob <col>

If the verdict is "poorly calibrated" or worse, fit on the calibration slice and apply to test:

    python skills/mde/scripts/calibration.py fix \
        --fit-path <cal_predictions.csv> \
        --apply-path <test_predictions.csv> \
        --y-true <col> --y-prob <col> \
        --method platt

Use `platt` unless the calibration set has ≥200 positives (the script refuses isotonic below
that). The script warns if AUPRC drops after calibration — a drop means the fit set isn't
representative, and is a stop-and-investigate signal, not a number to report.

Then run the post-calibration assertion gate:

    python scripts/gates/gate_assertions.py calibration \
        --pre-path <test_predictions.csv> --post-path <calibrated_probs.csv> \
        --y-true <col> --y-prob-pre <col> --y-prob-post <col>_calibrated

Any headline metric on the calibrated predictions must carry a bootstrap interval:

    python scripts/lib/bootstrap_ci.py <test_predictions.csv> \
        --y-true <col> --y-prob <col>_calibrated --metric <metric>

The calibration report is required evidence for the decision-optimization gate downstream.

### Step 8 — Champion selection

Run `python skills/mde/scripts/champion_selection.py select` to pick the Pareto-optimal champion (maximize metric, minimize complexity — parsimony wins ties).

Serialize the champion immediately — `champion.json` is metadata, not a model. Nothing
downstream (`model-handoff`, `inference.py`) can proceed without the fitted object:

```python
import joblib
joblib.dump(champion_model, ".eds/models/champion_model.joblib")
if calibrator is not None:
    joblib.dump(calibrator, ".eds/models/calibrator.joblib")
```

Record both paths in `champion.json` under `artifact_paths`.

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

Before marking the Plan entry `done`, record the code this stage actually ran:

    python scripts/lib/stage_code.py record --stage model --cells-json '<...>'

Record the *real* code — the pandas/sklearn that produced the numbers in the gate record,
not a paraphrase. `notebook-assembly` assembles the final notebook from these records; a
stage that doesn't record its code produces an empty cell in the deliverable notebook.

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
