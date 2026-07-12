---
name: explainability
description: >
  Explains a fitted champion model — global family-level SHAP attribution and
  local per-prediction reason codes mapped back to FDE catalog rationales. Use
  after MDE selects a champion and before decision-optimization sets thresholds.
  Gate: user-signoff (an explanation nobody reviewed is not an explanation).
  Do NOT use before a champion exists — hand off to `mde`. Do NOT use for
  feature selection — that's `fde`.
argument-hint: "[--model-path .eds/models/champion_model.joblib]"
license: MIT
---

# Explainability

This skill explains a *fitted champion*. It does not select features (that's FDE) and does
not justify a model that failed evaluation.

## Prerequisites

1. A fitted champion model at `.eds/models/champion_model.joblib`
2. A feature catalog at `.eds/features/feature_catalog.json` with `family` fields
3. Test/holdout data with the selected features

## MVP scope — two things only

### 1. Global: family-level SHAP

Raw per-column SHAP bars at 2000 features are noise. Aggregate SHAP values to the
*feature-family* level (using the FDE catalog's `family` field):

    python skills/explainability/scripts/explain.py global \
        --model-path .eds/models/champion_model.joblib \
        --data-path <test_data.csv> \
        --catalog-path .eds/features/feature_catalog.json \
        [--out .eds/models/explanation_global.json]

Output: a ranked table of feature families by total SHAP attribution — e.g.,
"aggregation features carry 40% of total attribution" is a finding;
2000 individual SHAP bars are not.

### 2. Local: per-prediction reason codes

For a set of predictions (typically the flagged/actioned cases), produce reason codes
mapped back to the FDE catalog's stated `rationale` for each feature:

    python skills/explainability/scripts/explain.py local \
        --model-path .eds/models/champion_model.joblib \
        --data-path <cases_to_explain.csv> \
        --catalog-path .eds/features/feature_catalog.json \
        --top-k 5 \
        [--out .eds/models/reason_codes.csv]

Output per row: top-k features by |SHAP|, each with the catalog's `rationale` field
(not a generic "feature X contributed 0.12" — the reason code should read like
"recency of last transaction (velocity family: recent activity signals engagement)").

## What is NOT in MVP

- **SHAP-vs-funnel consistency check** (does the champion's SHAP ranking agree with
  FDE stage-6 importance?). Deferred: nobody has asked for it and no decision
  currently hinges on it — rung 1 of the ladder.

# eds: deferred — SHAP-vs-funnel consistency check, no decision hinges on it yet

## Output

```
## Explainability: <champion name>
- global: <n> feature families ranked by SHAP attribution
  - top family: <name> (<pct>% of total attribution)
- local: <n> predictions explained with top-<k> reason codes
- gate: user-signoff required
```

## Handoff contract

Before marking the Plan entry `done`, record the code this stage actually ran:

    python scripts/lib/stage_code.py record --stage explainability --cells-json '<...>'

On completing this stage: (1) mark the Plan entry `done` with gate-record reference,
(2) proceed to `decision-optimization` — thresholds need the explanation context.
