---
name: model-governance
description: >
  Production pack for validation packages, approval workflow, audit
  evidence, bias review, model documentation, and regulatory
  traceability. The pack domain packs extend for regulated industries
  (credit-risk adds adverse-action explainability; fraud would add
  adversarial-drift review cadence). Not installed by default.
license: MIT
---

# Model governance (production pack)

## Ladder position

Only relevant for models heading to production in a regulated or high-stakes context — most sessions don't need this, and building a validation package for an exploratory notebook is over-build, not diligence.

## Owns

Validation packages, approval workflow, audit evidence, bias/fairness review, model documentation, regulatory traceability.

## The validation package checklist

1. **Data lineage** — where the training data came from, its snapshot/version (A5), and any known contract violations at ingestion (`data-contracts` if installed).
2. **Feature rationale** — every feature's hypothesis and funnel evidence, read directly from `fde`'s `feature_catalog.json` and `selected_features.md`, never re-derived from memory or restated informally.
3. **Bias/fairness slice metrics** — performance and error rates sliced by the protected/sensitive attributes relevant to the domain, not just an aggregate metric (this is `evaluation-design`'s segment-stability check, run specifically against fairness-relevant segments).
4. **Explainability artifact** — a stated method (SHAP summary, reason codes, a simpler surrogate model) appropriate to the domain's disclosure requirements, not a black-box score alone.
5. **Approval sign-off record** — who reviewed the package, what they flagged, and the resolution — a decision without a recorded reviewer is not yet governed.

## Extends

All Layer-1 skills feed evidence into the validation package (this pack doesn't re-derive them); domain packs extend this pack directly rather than restating governance logic — `credit-risk` adds adverse-action explainability requirements on top of this checklist, a fraud pack (not yet built) would add adversarial-drift review cadence.
