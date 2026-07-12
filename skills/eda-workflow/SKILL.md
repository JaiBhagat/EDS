---
name: eda-workflow
description: >
  Question-driven exploratory data analysis — every plot or summary stat
  answers a named question, never plot-spam. Use whenever someone asks to
  "explore this data", "what does the data look like", wants a first look at
  a new table, or asks for EDA/visualizations with no specific model or
  decision yet in view. Do NOT use once a specific model or decision-support
  question is already framed — hand off to `baseline-first` or `fde`; or if
  data trustworthiness is in question first, hand off to `data-audit`, then
  the relevant Layer-1 skill (`leakage-check`, `evaluation-design`, `fde`).
argument-hint: "[path-or-table]"
license: MIT
---

# EDA workflow

Same probe library `discovery` uses for the Problem Brief — this skill applies it to open-ended exploration instead of brief-writing. If `.eds/BRIEF.md` exists, read it first: the business objective there narrows which questions are worth exploring, so EDA doesn't have to guess.

## The rule: every plot answers a named question

Before making a plot or computing a summary stat, state the question it answers, in one line, first. If you can't state one, don't make the plot. A distribution histogram made "just to see" is the default failure mode this skill exists to stop — it burns tokens and reader attention without changing what anyone does next.

Hard cap heuristic: if a plot doesn't change what you (or the user) do next, don't make it. "Interesting" is not a reason; "changes the next step" is.

## Order of operations

1. **Audit first if not already done.** If this table hasn't been through `data-audit` this session, run that first — EDA on unvalidated data just produces confident-looking noise.
2. **Reuse the sampled probes**, don't hand-roll new ones for questions they already answer:
   - Grain / uniques → `skills/discovery/scripts/probes/schema_grain.py`
   - Missingness / structural nulls → `skills/discovery/scripts/probes/missingness.py`
   - Target shape (imbalance, distribution) → `skills/discovery/scripts/probes/target_profile.py`
   - Bivariate signal scan (which columns actually relate to what) → `skills/discovery/scripts/probes/quick_relationships.py`
   - Time coverage / seasonality shape → `skills/discovery/scripts/probes/time_coverage.py`
   - Table linkage → `skills/discovery/scripts/probes/linkage.py`
3. **Only build a custom plot/stat** once the sampled probes above don't answer the specific question in view — most "what does this look like" questions are answered by one of the six above, not a bespoke chart.

## Output

Report each finding as `<question> → <answer>`, not a chart-by-chart narration:

```
## EDA: <table>
- <question 1>? <answer, in one line, with the number>
- <question 2>? <answer>
```

If a question genuinely needs a one-off visualization the probes don't cover, produce it — but still lead with the question it answers, and say what changes as a result of the answer. An EDA pass that ends without "so now we should X" hasn't earned its cost.

## Boundaries

This skill produces understanding, not a model or a decision artifact. Once a specific hypothesis about a feature or model emerges from exploration, hand off to `fde` (feature hypotheses) or `baseline-first` (ready to model) rather than continuing to explore.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
