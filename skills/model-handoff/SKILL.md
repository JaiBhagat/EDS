---
name: model-handoff
description: >
  Serializes a champion model into a loadable bundle: model.joblib,
  calibrator.joblib, feature_spec.json, threshold.json, metrics.json,
  inference.py, MANIFEST.json. Use after champion selection and calibration
  are complete, before calling a model "done." The bundle is what makes later
  modularization mechanical — inference.py encodes the full raw-to-score
  pipeline so train/serve skew is impossible. Gate: MANIFEST hash recorded
  in the Brief's Plan row. Do NOT use before a champion is selected and
  evaluation is confirmed honest.
argument-hint: "[--model-path <path>] [--features <path>] [--threshold <path>]"
license: MIT
---

# Model Handoff

The missing step between "champion selected" and "model deployed." Nothing in the pipeline serializes a model until this skill fires. `champion.json` stores metadata only; this skill produces the actual loadable artifact.

## Prerequisites (checked, not assumed)

1. `.eds/models/champion.json` exists — a champion has been selected
2. `.eds/models/validation_contract.json` exists — evaluation is locked
3. `.eds/models/calibration_report.json` exists — calibration checked (not necessarily applied, but assessed)
4. A fitted model object is available (passed by the driving agent, or loaded from a prior stage)

If any prerequisite is missing, **stop and say which** — don't proceed with a partial bundle.

## The bundle structure

```
.eds/models/bundle/
  model.joblib            # fitted estimator (sklearn, xgboost, etc.)
  calibrator.joblib       # fitted calibrator (or None placeholder)
  feature_spec.json       # ordered feature list + dtypes + engineered-feature formulas
  threshold.json          # operating threshold(s) + tier map + cost assumptions
  metrics.json            # holdout metrics + bootstrap CI
  inference.py            # generated: load bundle, score a dataframe end-to-end
  MANIFEST.json           # hashes of all above + contract hash + seed + package versions
```

## Workflow

1. **Collect artifacts** — the driving agent passes the fitted model, calibrator (if any), feature list, threshold config, and holdout metrics.

2. **Serialize model + calibrator** — use `scripts/bundle_model.py`:
   ```
   python skills/model-handoff/scripts/bundle_model.py \
       --champion-path .eds/models/champion.json \
       --contract-path .eds/models/validation_contract.json \
       --out-dir .eds/models/bundle/
   ```
   The script handles joblib serialization and generates `inference.py` from the feature spec.

3. **Validate the bundle** — the generated `inference.py` must be importable and its `score(df)` function must accept a raw DataFrame and return calibrated scores. The script runs a smoke test.

4. **Compute MANIFEST** — SHA-256 of every file in the bundle, plus the contract hash, seed, and `pip freeze` of the environment.

5. **Record in Plan** — mark the model-handoff stage `done` with the MANIFEST hash as evidence.

## Generated inference.py contract

```python
def load_bundle(bundle_dir: str = ".eds/models/bundle/") -> dict:
    """Load all bundle components."""
    ...

def score(df: pd.DataFrame, bundle_dir: str = ".eds/models/bundle/") -> pd.Series:
    """Raw DataFrame → calibrated probability scores."""
    ...

def predict(df: pd.DataFrame, bundle_dir: str = ".eds/models/bundle/") -> pd.Series:
    """Raw DataFrame → binary predictions at the operating threshold."""
    ...
```

## Boundaries

- This skill serializes — it does NOT retrain, tune, or select. The model must already be fitted.
- Feature engineering logic is encoded in `feature_spec.json` as formulas/references, not re-implemented. If `features.py` exists (from P1.5), `inference.py` imports it directly.
- Threshold comes from `decision-optimization`'s output, not from this skill.

## Handoff contract

On completing this stage: (1) mark the Plan entry `done` with MANIFEST hash, (2) read the Plan, (3) proceed to the next pending stage (likely `ds-reporting` or `notebook-assembly`).
