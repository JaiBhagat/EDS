---
name: fde
description: >
  The Feature Discovery & Optimization Engine — the reasoning loop for
  signal search: what features should exist, hypothesis-first, evaluated
  through a staged funnel with a non-removable leakage gate, journaled so
  every accept/reject is traceable. Use whenever the request is about
  features, transformations, "what features should I build", signal
  search, feature selection, or a feature-engineering campaign of any
  size. Not a feature-engineering helper and not AutoML — it will refuse
  to generate a transformation without a stated hypothesis first. Runs
  inline for small campaigns (a dozen candidates); delegates to the
  `feature-scientist` agent for large ones (hundreds-to-thousands of
  candidates). Do NOT use for label/target definition (`label-design`) or
  for evaluating a finished model's metric (`evaluation-design`).
argument-hint: "[target|hypothesis-family|candidate-column]"
license: MIT
---

# FDE — Feature Discovery & Optimization Engine

Corollaries of A1–A6, specialized for feature search:

| # | Principle |
|---|---|
| F1 | Hypothesis before feature — no transformation without a stated, falsifiable claim about *why* it should carry signal. |
| F2 | Every feature earns its place, forever — acceptance is provisional; eviction is reasoned in the journal. |
| F3 | Signal is discovered, not manufactured — probe the data for what exists before inventing constructions over it. |
| F4 | Point-in-time or it doesn't exist — every candidate is checked against the feature-availability timeline. |
| F5 | A feature is code + data version + rationale — anything less is a column, not a feature. |
| F6 | Selection ends at the serving boundary — a feature set the operation can't run is a failed feature set. |
| F7 | The evaluation data is a budget, not a well — holdout touches are metered, not free. |

F7 is the principle a naive version of this engine always violates: a loop that evaluates thousands of candidates against one validation set *will* select noise. It shapes the evaluation funnel below.

## Never start on an unaudited table

Consume `data-audit`'s report first; if the target table hasn't been audited this session, hand off to `data-auditor` before doing anything else here.

## Read the Brief, not just the raw data

`.eds/BRIEF.md` already states the target, grain, feature-availability timeline, budget, and the success bar `baseline-first` set. A campaign's lift is measured against the **pre-FDE raw-feature baseline** — never against zero — so that baseline must already exist before a campaign starts.

## The loop

```
OBSERVE → HYPOTHESIZE → ASK/PROBE → ENGINEER → EVALUATE (funnel) → INTERPRET → PRUNE → repeat
```

1. **Observe** — read the Brief, the audit output, the current `feature_catalog.json`, and (round ≥2) the previous round's interpretation. What signal is already represented; what isn't?
2. **Hypothesize** — instantiate a family template from `references/hypotheses/*.md` against an observed gap. Each hypothesis is an object: `{id, family, claim, expected direction, cost estimate, availability check, priority}` — never a vibe.
3. **Ask / Probe** — the Discovery prime directive applies verbatim: ask the user about the world, ask the data about the data. Domain meaning goes to the user in small batches; anything measurable (does the link table actually join? what's event density per entity?) is a sampled probe — use `scripts/probes/structure_probes.py`.
4. **Engineer** — build candidates for surviving hypotheses only, point-in-time correct by construction, one function per feature, registered in `feature_catalog.json` at birth via `scripts/catalog.py`.
5. **Evaluate** — run the staged funnel (`scripts/evaluators/funnel.py`, stages below). Cheap gates first; expensive gates see only survivors.
6. **Interpret** — not just scores: *why* did this family work or fail? A rich signal in one window suggests probing adjacent windows; a failed ratio family kills its siblings cheaply, before they're even engineered.
7. **Prune** — evict, and write the reason to `feature_journal.md`. A rejected hypothesis with a reason is institutional knowledge; without one it's a future duplicate effort.

## The hypothesis families

Sixteen templates in `references/hypotheses/`: `behavioral`, `temporal`, `velocity`, `frequency`, `aggregation`, `ratio`, `trend`, `interaction`, `graph`, `sequence`, `seasonality`, `anomaly`, `peer-comparison`, `lifetime`, `business-rule`, `external-enrichment`. Each states its claim pattern, precondition probe, construction recipe, and canonical failure modes — read the relevant one before instantiating a hypothesis in that family, don't improvise around it.

Core ships the families with no domain weighting. A domain pack may re-weight family priority (fraud boosts velocity/graph/anomaly) or add vocabulary, but never add loop logic or remove a funnel stage.

## The evaluation funnel

One pipeline, cheapest-first and never-cut-first (`scripts/evaluators/funnel.py`):

| Stage | Gate | Hard-kill? |
|---|---|---|
| 0 | Leakage scan | yes — never-cut, never removable |
| 1 | Degenerate filter (constants, duplicates) | yes |
| 2 | Missingness & coverage | yes |
| 3 | Cardinality & encodability | yes |
| 4 | Univariate signal (correlation/MI/IV) | no — ranks only, interaction families pass through regardless |
| 5 | Redundancy (correlation clustering) | yes |
| 6 | Model-based importance (rotating fold) | no — ranks only |
| 7 | Stability across time slices | yes |
| 8 | Business explainability review | human sign-off, tracked not auto-evicted |
| 9 | Serving review (cost, latency, parity) | yes |
| 10 | Final selection + confirmation holdout | terminal — touched once per campaign |

Full metadata per stage (cost class, applicable task types, output schema) lives in `references/evaluators/stage-*.md`. Stage 0 delegates adversarial passes on suspicious candidates to `leakage-hunter`.

**F7 mechanics:** stages 4–7 run on rotating folds/time-slices; stage 10's confirmation holdout is touched once per campaign, enforced by `stage_10_confirmation` refusing a second call — a genuine re-touch needs an explicit `# eds: deferred — holdout re-use` marker, never a silent second look.

## Stopping criteria — the loop terminates on the first of

1. **Marginal-gain floor** — best surviving candidate improves the metric by less than the Brief's floor (default: less than the metric's cross-fold standard error).
2. **Hypothesis-space exhaustion** — all families instantiated against all observed structures; remaining ideas need data the org doesn't have — route those to the Brief's gap list, not to more engineering.
3. **Budget** — compute/token/holdout-touch budget from the Brief consumed. The ladder applies to the search itself: rung 1 asks whether the *next round* needs to exist.
4. **Stability plateau** — new candidates keep failing stage 7; the data's signal at this grain is captured.
5. **Good-enough bar** — the Brief's success bar is met with margin.

On stop, write the campaign summary to `feature_journal.md` including which criterion fired.

## Artifacts

Schemas in `references/artifacts-schema.md`. Only `feature_catalog.json` and the current round's `candidate_features.md` load into context by default — `feature_journal.md` and `experiment_log.md` are grepped on disk, never bulk-loaded.

## Inline vs. delegate

Run the loop **inline** for a small campaign (a dozen candidates on a notebook problem) — the method must work without delegation, or it isn't a method. For a full campaign (hundreds-to-thousands of candidates), delegate to the `feature-scientist` agent: it keeps the campaign's intermediate noise out of the main thread and returns only round summaries and the final selected set.

## Output

```
## Feature round: <target>, round <n>
- hypotheses instantiated: <n>, families: <list>
- funnel: <n> in → <n> survived stage 0-3 → <n> survived stage 5 → <n> ranked at stage 6/7
- selected this round: <n>, evicted: <n> (reasons in journal)
- stopping check: <criterion met? y/n>
```

Every accept/reject decision must be traceable to a `feature_journal.md` entry.

## Pipeline output (P1.5)

At campaign end, the FDE stage produces **two artifacts** beyond the journal:

1. **`.eds/features/feature_spec.json`** — ordered feature list + dtypes + formulas for engineered features
2. **`.eds/features.py`** — a `build_features(df) -> df` function that reproduces the full feature-engineering pipeline

The `features.py` file is the **single source of truth** for feature transforms. Both the notebook and `inference.py` (model-handoff) import it. This prevents train/serve skew.

Generate with:
```
python skills/fde/scripts/export_features_pipeline.py \
    --catalog-path .eds/features/feature_catalog.json \
    --out-dir .eds/features/
```

The generated `features.py` encodes:
- Column selections and type coercions
- Engineered feature formulas (from the catalog's `formula` field)
- Feature ordering matching the model's training order
- A `FEATURE_NAMES` constant for downstream consumers

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
