---
name: model-monitoring
description: >
  Monitors a deployed model for input drift and decision-quality decay —
  PSI/KS on features, plus queue-size/action-rate tracking so a "still
  accurate" model that's silently degrading the operation gets caught (axiom
  6). Use whenever someone asks about production model health, "the model
  seems worse", drift, retraining triggers, or alert thresholds for a live
  model. Do NOT use for pre-launch validation — that's `evaluation-design`
  and `model-governance`. This skill is specifically post-deployment.
argument-hint: "[reference.csv current.csv]"
license: MIT
---

# Model monitoring

Axiom 6 operationalized for the post-deployment phase: a model can hold its offline metric and still be failing the operation it serves (a queue overwhelmed, an action rate collapsed) — this skill watches both the statistical signal (is the input distribution shifting) and the operational signal (is the decision still sane), not just the former.

## Input drift

Run `skills/model-monitoring/scripts/drift_check.py <reference.csv> <current.csv> [--cols col1,col2] [--psi-threshold 0.25]` — it computes PSI (Population Stability Index) per numeric/categorical column between the reference window (e.g. training data, or last-known-good) and the current window. Interpretation: PSI < 0.1 negligible shift, 0.1–0.25 moderate (watch), > 0.25 significant (investigate before trusting current predictions). PSI drifting on a feature the model actually depends on (check `fde`'s `feature_catalog.json` if this campaign used it) is a stronger signal than drift on an unused column — weight accordingly, don't treat every flagged column equally.

## Label decay and retraining triggers

Real-time performance metrics need ground truth, which usually arrives late or not at all in production. State explicitly how and when labels become available for this model (immediately, next-day batch, only on a chargeback/complaint, never for most rows) — a monitoring plan that assumes labels arrive faster than they actually do will alert on stale non-issues or miss real decay. Retraining triggers should be tied to a stated threshold on drift or decayed-label performance, decided in advance, not "whenever it feels off."

## Decision-quality monitoring (the axiom-6 half, don't skip this)

Score distribution drift is necessary but not sufficient — track the metrics that reflect whether the *decision* the model feeds is still sane:

- **Queue/volume size** — is the number of cases flagged for review/action within the operational capacity stated in the Brief? A score distribution shift that changes the volume flagged, even with a stable AUC, is an operational regression.
- **Action rate** — of cases the model recommends acting on, what fraction actually get acted on (and does that match what was true at launch)?
- **Realized value** — where measurable, the actual downstream outcome (fraud caught, churn prevented) rather than only the proxy score.

A model that's "still 0.85 AUC" but has quietly doubled the review queue or halved the action rate has failed by axiom 6, even though every score-based check passed.

## Output

```
## Monitoring: <model>
- input drift: <n> cols flagged (PSI>threshold): <col>: PSI=<v>, ...
- label availability: <lag/coverage>, last confirmed performance: <metric, date>
- decision quality: queue size <now vs baseline>, action rate <now vs baseline>
- retraining trigger: <met/not met> — <threshold and current value>
```

If decision-quality numbers aren't available for this deployment (no volume/action-rate instrumentation), say so as a gap: `# eds: deferred — no decision-quality instrumentation, monitoring is score-distribution-only`.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
