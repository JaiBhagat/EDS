# Problem Brief schema

`.eds/BRIEF.md` is the fixed-schema artifact the Discovery Loop produces and every downstream skill reads from. Compressed to ~1–2k tokens. Fill every section; write "N/A — <why>" rather than omitting one.

```markdown
# Problem Brief

## Status
draft | confirmed | no-go
version: 1
last-confirmed: <date>

## Decision
What decision does this analysis change? Who acts on the output, at what cadence?

## Stage 0 — Value & solution class
- Value estimate: expected lift × decision volume × value per decision, minus build+run+maintain cost (order of magnitude).
- Suitability: is the prediction actionable? enough data/label signal? operational constraints?
- Solution-space scan: rule / SQL+threshold / search / graph / optimization / LLM call / hybrid / ML / no-solution — and why the chosen class won.
- Considered-and-rejected alternatives: <list>
- Verdict: GO | NO-GO. If NO-GO, stop here — this is a success outcome, not a failure.

## Confirmed problem statement
"You want to decide X, at cadence Y, wrong costs Z — correct?" — the user-confirmed restatement.

## Data inventory
| Source | Grain | Time coverage | Access | Status (have/missing/proxy) |
|---|---|---|---|---|

## Target & label strategy
Definition, delay/censoring, proxy/weak-label bias if any, gold-set plan if any. (Hands off to `label-design` skill when labels are delayed, proxy, or weak.)

## Unit & grain
Unit of prediction/analysis. Grain of the modeling table.

## Time semantics
Does time matter? Observation window / performance window structure if so. History depth vs. horizon needed.

## Task type
supervised/unsupervised · regression/classification/forecasting/other

## Operational constraints & consumption path
Who consumes the prediction, at what capacity (review queue size, latency, channel)? Constraints that bound the solution (compute, latency, explainability, regulatory).

## Success metric & baseline bar
Metric matched to the decision's cost asymmetry AND operational capacity (A6). The baseline the complex approach must beat, and by how much.

## Open questions & deferred items
Anything routed to `eds: deferred` or back to gap analysis (e.g. external-enrichment hypotheses).

## Plan
Ordered lifecycle checklist, instantiated from the task type. Each entry:
- <stage> · <owner-skill> · <status(pending|in-progress|done|skipped — reason)> · <gate(none|user-signoff|gate-record ref)>

Example (supervised prediction):
- audit · data-audit · pending · none
- eda · eda-workflow · pending · none
- label-design · label-design · pending · user-signoff
- evaluation-contract · evaluation-design · pending · user-signoff
- fde · fde · pending · none
- baseline · baseline-first · pending · none
- model · model · pending · none
- calibration · model · pending · none
- decision-optimization · decision-optimization · pending · user-signoff
- report · ds-reporting · pending · none
- monitoring-handoff · model-monitoring · pending · user-signoff
```

## Gating rules

- No confirmed Brief in `full`/`ultra` mode → model-building/feature skills trigger discovery instead of proceeding.
- Material changes to the problem (new target, new population) → re-confirmation pass, not a full re-run. Bump `version`, keep prior sections as history if useful.
- A NO-GO verdict at Stage 0 is a complete, successful Brief. Nothing downstream should run against it except the one-page no-go writeup.
