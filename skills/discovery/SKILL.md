---
name: discovery
description: >
  The front door of EDS. Runs a stateful, multi-turn Discovery Loop that turns
  a vague ask into a confirmed Problem Brief (.eds/BRIEF.md) before any plan,
  EDA, or feature work happens. Use this at the START of any new data science
  problem: a first message about a dataset, "help me build/predict/analyze
  X", "should we launch Y", a fresh project with no .eds/BRIEF.md, or any ask
  underspecified enough that you'd otherwise have to guess the decision, the
  cost of being wrong, or what "done" means. Also use to resume an in-progress
  Brief, or via /discover. Do NOT use once a confirmed Brief already exists
  for this exact problem — hand off to `eds-core` and read the Brief instead
  (see brief.md command). Do NOT use
  for narrow, already-scoped requests ("add a null check to this query",
  "what's the p95 of this column") — those don't need discovery, they need
  the answer.
argument-hint: "[resume|restart]"
license: MIT
---

# Discovery

Seven gated stages. Output is `.eds/BRIEF.md`, signed off by the user. Nothing downstream (EDA, features, modeling) proceeds without it in `full`/`ultra` mode.

**Prime directive:** ask the user about the world; ask the data about the data. Never ask a question a sampled probe can answer (null rates, cardinality, date ranges, table linkage). Spend the user's attention only on business objective, cost of being wrong, cadence, data beyond what was shared, domain expectations, constraints.

**Batching rule:** 2–4 questions per turn, never a long form. Prune downstream questions based on answers already given.

## Stage 0 — Decision & architecture

Before anything else: what is the decision worth, and is a model the right tool *class*?

- **(a) Value estimate** — expected lift × decision volume × value per decision, minus build+run+maintain cost. Order-of-magnitude, not a business case.
- **(b) Suitability** — is the prediction actionable? Who consumes it? Enough data and label signal? Operational constraints?
- **(c) Solution-space scan** — rule? SQL+threshold? search? graph? optimization? LLM call? hybrid? **no solution** (status quo is fine)?

A NO-GO here is a **success outcome** — write the one-page no-go brief (Stage 0 fields of `brief-schema.md`, verdict NO-GO) and stop. This is rung 1 of the ladder made explicit at tool-class level.

## Stage 1 — Problem

Ask for the problem statement using `references/questions/universal.md` Q1–Q3 (decision, action, cost asymmetry), batched. Then **restate it in decision language**: "You want to decide X, at cadence Y, wrong costs Z — correct?"

No confirmation → do not proceed to Stage 2. Re-ask or refine.

## Stage 2 — Inventory

"What data do you have?" — tables, files, grain, rough time coverage, where it lives, access constraints. Universal bank Q4 (population) helps scope this. Record as a table: source / grain / time coverage / access / status.

## Stage 3 — Gap analysis

Experience-driven, not a blank slate. Classify the archetype (prediction, forecasting, measurement — see `references/questions/universal.md` for the full list and current archetype coverage), pull the matching bank from `references/questions/`, and ask about the delta between what a problem of this shape *typically* uses and what's been shared. Record each item as **have / missing / proxy**.

If the archetype needs external data the org may have but didn't share, flag it under `external-enrichment` in the Brief's open-questions section — this is a live extension point the `fde` skill's hypothesis families also feed.

## Stage 4 — Probes

Run the sampled probes in `scripts/probes/` against whatever's actually been shared. Fast and cheap by design — minutes, not an EDA project:

| Probe | Answers |
|---|---|
| `schema_grain.py` | What is each table's grain, and does the data honor it? |
| `missingness.py` | Where are the holes, random or structural? |
| `target_profile.py` | Target balance, distribution, definition sanity? |
| `time_coverage.py` | What windows exist, gaps, does history reach the needed horizon? |
| `linkage.py` | Do tables actually join, at what cardinality? |
| `quick_relationships.py` | Which fields plausibly carry signal (corr/MI on a sample); leakage-suspect flags? |

Run each with `python <probe>.py <path-or-table> [args]` against a **sample**, not the full dataset. Each probe prints a compact structured block — paste it into the Brief verbatim, don't re-summarize in prose.

**Anything a probe flags as leakage-suspect** (a feature perfectly separating the target, a timestamp after the outcome) gets raised now, before a single feature is engineered — don't defer it to `leakage-check`.

## Stage 5 — Framing

From the confirmed objective + probed data, determine:

- **Target & label strategy** — hand off to `label-design` skill if labels are delayed, proxy, or weak.
- **Unit of prediction/analysis**, supervised/unsupervised, task type.
- **Time semantics** — does time matter; if so, observation/performance window structure.
- **Success metric** — matched to the decision's cost asymmetry AND operational capacity (axiom 6), plus the baseline it must beat.

## Stage 6 — Brief + Plan

Compile everything into `.eds/BRIEF.md` per `references/brief-schema.md`. Then append a `## Plan` section — an ordered, Brief-derived lifecycle checklist instantiated from the task type:

**Supervised prediction:** `audit → eda → label-design → evaluation-contract → fde → baseline → model → calibration → decision-optimization → report → monitoring-handoff`

**Measurement / experiment:** `audit → experiment-design → analysis → report`

**Forecasting:** `audit → eda → fde → baseline → model → report → monitoring-handoff`

Each Plan entry: `- <stage> · <owner-skill> · <status> · <gate>`. Status is one of `pending | in-progress | done | skipped — <reason>`. Gate is `none`, `user-signoff`, or a gate-record reference. Skipping a stage requires a reason — the deferred-marker convention applied to the lifecycle.

Also emit `.eds/PROJECT.md` per `references/project-template.md` — the project operating manual: data access, environment, how-to-run, conventions. This is the AGENTS.md of the data project — any future session reads it to know how to work HERE.

If no `CLAUDE.md` exists at the project root, emit one per `references/claude-md-template.md` — behavioral guardrails for LLM-assisted DS work (think-before-coding, simplicity-first, audit-before-analyze, baseline-before-complex, reproducibility, leakage prevention, anti-patterns). This file works standalone — even without the EDS plugin loaded, the project's CLAUDE.md enforces DS discipline. If a `CLAUDE.md` already exists, append an `## EDS Data Science Discipline` section with the DS-specific rules only (sections 5–7 from the template), preserving the user's existing guidelines.

Present the Brief + Plan + PROJECT.md to the user for sign-off. Discovery closes on confirmation; the workflow spine takes over.

## Resuming and overriding

- **Resume**: if `.eds/BRIEF.md` exists with `status: draft`, continue from the last completed stage — don't restart Stage 1.
- **Material change** (new target, new population): bump `version`, run a re-confirmation pass on the affected sections only, not a full re-run.
- **Explicit skip**: user says "skip discovery" → proceed, but write `eds: deferred — no brief` to the debt ledger. This makes the shortcut visible, not silent.
- **Lite mode**: the gate is advisory — offer discovery, don't block on it.

## What this is not

Not a 40-question intake form — that kills adoption. Not a replacement for reading the data; the probes exist because the data can answer things faster and more honestly than a user's memory of it. Not required for narrow, already-scoped asks — see this skill's description for the boundary.
