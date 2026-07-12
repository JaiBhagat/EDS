---
name: eds-core
description: >
  The always-on data-science operating philosophy for EDS. Loads the ladder
  (understand → skip → reuse → query → EDA → heuristic → baseline → library →
  custom model), the six axioms, and the never-cut list (data validation,
  leakage prevention, honest evaluation, uncertainty honesty, reproducibility,
  privacy). Use this as the reasoning frame for ANY data science, analytics,
  statistics, or ML task: exploring data, building a model, designing an
  experiment, writing a report, reviewing a notebook, or deciding whether an
  analysis should exist at all. Every other EDS skill assumes this is loaded
  and never restates it. Trigger words: "analyze", "build a model", "predict",
  "should we", "is it worth", "explore this data", "eda", "feature", "metric",
  "baseline", "leakage", "reproduce", or any mention of a dataset/table/notebook.
license: MIT
---

# EDS core

Full ruleset lives in the plugin's `EDS.md` (loaded at session start as a digest). This skill is the operational trigger — when it fires, apply `EDS.md` in full, not just the digest.

## What this skill does on trigger

1. **Classify the request** against the ladder before writing any code. State which rung you're stopping at, in one line, before producing output — not after.
2. **Check for a confirmed Brief** (`.eds/BRIEF.md`). In `full`/`ultra` mode: no confirmed Brief on a new problem → hand off to the `discovery` skill instead of proceeding. In `lite` mode: proceed, but note the gap.
3. **Read before deciding.** Trace the actual data/code the task touches — schema, grain, current pipeline — before picking a rung. This is not optional at any mode.
4. **Apply the never-cut list** regardless of rung. A rung-3 crosstab still needs a grain check if it's answering a decision. A rung-8 custom model still needs an out-of-time holdout.
5. **Mark deferrals.** Anything deliberately skipped gets `# eds: deferred — <reason>` inline, not silence.

## Delegation map

This skill decides *which* other EDS skill or agent owns the next step — it doesn't do the work of `data-audit`, `leakage-check`, `baseline-first`, etc. itself. Route:

| Situation | Hand off to |
|---|---|
| New problem, vague ask, first contact with a dataset | `discovery` |
| New table/file, any join | `data-audit` (or `data-auditor` agent) |
| "Explore this data", open-ended EDA, no model/decision framed yet | `eda-workflow` |
| Features, splits, "train a model", temporal data | `leakage-check` |
| Metrics, "how good is", model comparison | `evaluation-design` |
| Target/label definition, weak supervision | `label-design` |
| Thresholds, precision/recall tradeoff, review queue | `decision-optimization` |
| "Build a model", "predict" | `baseline-first`, then the ladder decides if it goes further |
| Baseline measured but not good enough, "improve the model", multi-round modeling | `mde` (or `model-scientist` agent for large campaigns) |
| Calibration check, probability calibration | `mde` (Step 7 — calibration before thresholds) |
| Feature transformations, signal search | `fde` |
| A/B test, experiment, launch decision | `experiment-design` |
| Model is wrong, debugging performance | `error-analysis` |
| Production, drift, "model degraded" | `model-monitoring` |
| Write-up, present, stakeholder-facing | `ds-reporting` |
| Notebook cleanup, promotion to script/pipeline | `notebook-hygiene` |
| Reviewing a diff/notebook for rigor or over-build | `/eds-review` → `ds-code-reviewer` agent |

## The drive rule

When a Plan exists in `.eds/BRIEF.md`: after completing any stage, read the Plan, identify the next pending stage, and proceed into it. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage. If the next stage carries a `user-signoff` gate, present the decision and stop — but don't ask "what next?", ask the specific gate question. In `lite` mode, propose instead of proceed.

## Verification gates (H3)

Before marking any Plan stage `done`: run its gate (`python scripts/gates/gate_<stage>.py`). The gate writes a pass/fail record to `.eds/verification/`. A stage is not done until the gate passes — no exceptions, no self-attestation. If a gate fails, fix the cause; do not mark the stage done and move on.

## Output discipline

State the rung, then the answer. Decision-first: answer → confidence → caveats → recommendation. If the right answer is "don't build this," say that plainly and stop — a correctly-avoided rung-8 build is a success, not an unfinished task.
