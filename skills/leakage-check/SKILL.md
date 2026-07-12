---
name: leakage-check
description: >
  Hunts for leakage before a model is trusted — axiom 4, "time flows one
  way." Traces feature derivation for post-outcome timing, scans splits for
  entity overlap, and mandates an out-of-time or properly held-out
  evaluation. Use this whenever features are being built, a train/test split
  is being designed, a model is about to be trained, or the data has any
  temporal structure at all. Also trigger on: "why is this model so good",
  suspiciously high accuracy/AUC early in a project, a feature whose name
  suggests it's computed downstream of the outcome (e.g. "resolution_time",
  "final_status", "chargeback_flag" as a fraud feature). Do NOT use for
  pure descriptive/EDA work with no model or decision-time constraint —
  hand off to `eda-workflow` instead; this skill is specifically about
  point-in-time correctness for prediction.
argument-hint: "[feature-list|split-description]"
license: MIT
---

# Leakage check

Never-cut item 2, operationalized. If `.eds/BRIEF.md` exists, its time-semantics and operational-constraints sections state what "available at decision time" means for this problem — read that before scanning, don't re-derive it from scratch.

## The four checks, in order

### 1. Feature-availability timeline

For every candidate feature, ask: at the moment this prediction is actually made, does this value exist yet? Build (even informally, as a short table) a timeline: decision point → what's known up to that point → what's only known after. Anything on the "after" side is not a feature, no matter how predictive.

Common failure patterns to check by name and by construction:
- Aggregates computed over a window that extends past the decision point ("total spend this month" computed on a month that isn't over yet at decision time).
- Status/outcome fields that are themselves late-arriving (a "resolved" flag, a "final" anything, a chargeback/refund flag for a fraud model).
- Joins to a table that's updated retroactively (a CRM field edited after the fact to reflect what actually happened).

### 2. Target-derivation trace

Trace exactly how the target column is computed. If any input to that computation is *also* a feature (even indirectly, through a derived column), that feature is leaking the target into itself. This is the single most common real-world leak — a feature and the label sharing an upstream source column under different names.

### 3. Entity-overlap scan across splits

The same entity (customer, account, device — whatever the grain is) must not appear in both train and evaluation splits. Run `skills/leakage-check/scripts/split_overlap.py <train.csv> <eval.csv> --key <entity-col>` to check. For time-series/panel data, a random split leaks by construction — the split must be time-based (train on the past, evaluate on the future), never shuffled.

### 4. Out-of-time holdout mandate

A held-out set drawn from a *later* time window than training is worth more than a larger same-window random holdout — it's the only split that actually tests what production will face. If the evaluation isn't out-of-time and time plausibly matters (check the Brief's time-semantics section), that's a gap to close, not a stylistic preference.

## Quick leakage smell test

Run `skills/leakage-check/scripts/feature_availability_scan.py <path> --target <col> --cutoff-col <date-col>` against the modeling table: it flags (a) features perfectly or near-perfectly separating the target (reuses the same signal the `quick_relationships.py` discovery probe surfaces — if this wasn't already run during discovery, run it now), and (b) any column whose name pattern suggests post-outcome computation.

## Output

State pass/fail per check, not a narrative. A single leaked feature found late is cheaper to report as: `LEAK: <feature> — derived from <target-source-column>, drop it.` than to explain at length.

If a check can't be completed (e.g. no timestamp exists to verify availability), that is itself a finding: `# eds: deferred — cannot verify point-in-time availability for <feature>, no timestamp on source table`.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
