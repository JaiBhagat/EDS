---
name: error-analysis
description: >
  Diagnoses *why* a model is wrong before reaching for more modeling — slice-
  based error analysis and the is-it-data/label/model triage. Use whenever a
  model's performance is disappointing, someone asks "why is this model
  wrong", wants to debug a specific set of mispredictions, or is about to
  propose a fix (more features, a different algorithm, more data) without
  having looked at where the errors actually concentrate. Do NOT use for
  initial model comparison against baseline — that's `evaluation-design`.
  This skill is specifically post-hoc diagnosis of an underperforming model.
argument-hint: "[path.csv --y-true col --y-pred col]"
license: MIT
---

# Error analysis

Look before proposing a fix. A model's aggregate metric hides *where* it's wrong — the fix for "wrong everywhere a little" (more/better features) is different from "wrong badly on one segment" (a label problem or a missing feature specific to that segment) or "wrong on mislabeled examples" (a label-quality problem no amount of modeling fixes).

## The triage: is it data, label, or model?

Before slicing, check the cheap explanations first — they're more common than people expect and cheaper to confirm:

1. **Data problem?** Are the worst-error rows missing values, out-of-range, or otherwise the kind of row `data-audit` should have flagged? If so, the fix is upstream, not in the model.
2. **Label problem?** Pull a sample of the worst mispredictions and manually inspect the labels. Noisy or wrong labels produce errors that look like model failure but aren't — no model can be evaluated fairly against a target it's not actually being asked to predict.
3. **Model problem?** Only once 1 and 2 are ruled out (or quantified) does "the model needs more capacity/features/data" become the right conclusion.

## Slice-based error analysis

Run `skills/error-analysis/scripts/slice_errors.py <path.csv> --y-true <col> --y-pred <col> [--slice-cols region,segment,channel] [--metric auto]` — it computes the error metric overall and per slice for each named slicing column, and flags slices whose error rate is significantly worse than the overall rate (not just numerically different — small slices produce noisy rates by chance). Pick slice columns with a domain reason (segments the Brief or business already treats differently), not every column in the table — a fishing expedition across dozens of slices will find "significant" noise by chance alone.

## Residual triage (regression) / confusion breakdown (classification)

For regression, look at the sign and magnitude pattern of residuals across the flagged slice(s) — systematic over- or under-prediction in one slice points at a missing feature specific to that segment, not random noise. For classification, break the worst slice down by confusion-matrix cell (false positives vs. false negatives) — the two error types often have different causes and different fixes.

## Output

```
## Error analysis: <model/target>
- overall: <metric>
- worst slice: <slice-col>=<value> — <metric> (n=<size>), <significant/not>
- triage: data | label | model — <one-line evidence>
- recommended next step: <specific, tied to the triage above>
```

Don't recommend "collect more data" or "try a different model" without a specific slice/failure mode driving that recommendation — a vague fix is a sign the triage step was skipped.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
