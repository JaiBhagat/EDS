---
name: data-audit
description: >
  Audits a dataset before any analysis touches it — axiom 2, "the data is
  guilty until proven innocent." Runs grain assertion, null/duplicate/range
  profiling, join-cardinality checks, and time-coverage checks, then emits a
  compact audit block. Use this whenever a new table, file, or dataset enters
  the conversation: "load this csv", "here's our data", a new join, a new
  data source added to an existing analysis, or before building on top of any
  table not already audited this session. Also invoke before `leakage-check`,
  `baseline-first`, or `fde` run on a dataset that hasn't been through this
  first. Do NOT use on a table already audited earlier in the same session
  with no changes since — re-running an unchanged audit is waste, not rigor.
argument-hint: "[path-or-table] [--grain col1,col2]"
license: MIT
---

# Data audit

Never-cut item 1, operationalized. Read `EDS.md` first if this is the first skill firing this session — this skill assumes the ladder and never-cut list are already loaded.

## When this is Brief-aware

If `.eds/BRIEF.md` exists, read its data-inventory table first — it already states expected grain and time coverage for tables you catalogued during discovery. This skill *verifies* those claims against the actual data; it doesn't re-ask the user what the Brief already recorded.

## The checklist (in order — cheap checks first)

1. **Grain assertion** — run `skills/discovery/scripts/probes/schema_grain.py <path> --grain <candidate-cols>`. If no candidate grain is known yet, run without `--grain` to see suggested unique-key candidates first, then confirm the real grain with the user or the Brief before treating it as settled.
2. **Nulls & structural missingness** — run `skills/discovery/scripts/probes/missingness.py <path>`. A null-indicator correlation flag means the missingness is likely structural (a shared cause), not random — note this, don't silently impute past it.
3. **Duplicates** — covered by the grain check (step 1): duplicate rows on the asserted grain is a grain violation, not a separate step. If grain is intentionally many-per-entity (e.g. an event log), state the real grain and check duplicates on *that* instead.
4. **Range checks** — run `skills/data-audit/scripts/range_check.py <path>` for a fast auto-profile (min/max/percentiles per numeric column, flags likely sentinel values like -1, 9999, 0 where implausible). Anything domain-specific ("age can't exceed 120", "a rate can't be negative") needs the user's domain knowledge — ask, don't assume a bound the data alone can't tell you.
5. **Join cardinality** — for any join this analysis performs, run `skills/discovery/scripts/probes/linkage.py <left> <right> --left-key <k> --right-key <k>` *before* trusting a post-join row count. A many:many join is a hard stop until the cardinality is understood, not just noted.
6. **Time coverage** — if the table has a date/timestamp column, run `skills/discovery/scripts/probes/time_coverage.py <path> <date-col>`. Gaps or truncated recent history change what horizon is honestly supportable.

## Output

Emit one compact audit block per table, not a narrative:

```
## Data audit: <table>
- grain: <cols> — PASSED/FAILED (<n> dupes)
- nulls: <col>: <rate>% [structural if flagged]
- range flags: <col>: <finding>
- join <left>-<right>: <cardinality>, <match-rate>
- time coverage: <span>, <gaps>
```

If any check fails, the analysis does not proceed past it silently — either fix the data issue, or mark it explicitly: `# eds: deferred — <reason>` and say what's now unreliable because of the skip.

## Wide-table triage (>100 columns)

When the joined table exceeds ~100 columns, run the column triage before FDE starts:

    python skills/data-audit/scripts/column_triage.py <path.csv> --target <col> \
        [--source-label main] [--out .eds/data/column_triage.csv]

This produces a per-column triage table (`DROP-CANDIDATE`, `HIGH-SIGNAL`, `NEEDS-DOMAIN-INPUT`, `LOW-PRIORITY`) and a markdown summary. The `NEEDS-DOMAIN-INPUT` bucket is the discussion list — surface these to the human explicitly. **This skill does NOT drop anything.** It buckets and reports; the human and the FDE funnel decide.

## Boundaries

This is a probe-driven check, not an EDA. If a finding raises "why does this look like this" (a business question), stop and ask the user — don't guess a domain explanation for a data anomaly. Hand off exploratory questions beyond audit scope to `eda-workflow`.

## Handoff contract

Before marking the Plan entry `done`, record the code this stage actually ran:

    python scripts/lib/stage_code.py record --stage data_audit --cells-json '<...>'

Record the *real* code — the pandas/sklearn that produced the numbers in the gate record,
not a paraphrase. `notebook-assembly` assembles the final notebook from these records; a
stage that doesn't record its code produces an empty cell in the deliverable notebook.

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
