---
name: notebook-hygiene
description: >
  Governs the notebook → parameterized script → tested pipeline maturity
  ladder — when to promote a notebook to something more durable, and when
  explicitly not to. Use whenever someone wants to clean up a notebook,
  asks whether something should become a script/pipeline, or a notebook is
  about to be handed off/scheduled/relied on repeatedly. Do NOT use for a
  one-off exploratory notebook that answers a question once and is done —
  promoting throwaway exploration is over-build, not hygiene; hand off to
  `eda-workflow` instead.
argument-hint: "[notebook.ipynb]"
license: MIT
---

# Notebook hygiene

Rung logic (from `EDS.md`'s ladder) applied to artifact maturity, not just to whether to build something at all. A notebook that's rerun once and done needs none of this; a notebook that's about to be scheduled, shared, or rerun repeatedly needs to climb the ladder below.

## The maturity ladder

1. **Exploratory notebook** — cells run out of order is fine, no parameterization needed, disposable. Appropriate for one-off EDA (`eda-workflow`) or a single analysis that answers one question and won't be rerun.
2. **Parameterized script** — top-of-file parameters (not hardcoded mid-cell), runs top-to-bottom without manual intervention, no dead cells. Appropriate once the same analysis needs to run again with different inputs (a new date range, a new segment).
3. **Tested pipeline** — the script above plus a reproducibility path (seeds, versioned inputs, one command reruns it — never-cut item 5) and at least one check that fails loudly if the logic breaks. Appropriate once the output feeds a recurring decision, a schedule, or another person/system depends on it.

**Promote one rung when the notebook's actual usage pattern changes** (someone else needs to rerun it, it's about to be scheduled, its output is about to feed a decision more than once) — not preemptively "just in case." A notebook promoted to rung 3 that's actually only ever run once by its author is wasted ceremony; the ladder runs both directions.

## Checking readiness

Run `skills/notebook-hygiene/scripts/maturity_check.py <notebook.ipynb>` — it scans cell source for promotion-readiness signals: hardcoded absolute paths (rung-2 blocker — parameters should be defined once, at the top, not scattered inline), presence/absence of a seed (rung-3 blocker per never-cut item 5), out-of-order execution counts (a rung-1 tell — fine there, a smell at rung 2+), and defined functions vs. inline copy-paste (repeated inline logic is a sign the notebook has outgrown rung 1 without being promoted).

## Output

```
## Notebook maturity: <file>
- current signals: <n> hardcoded paths, seed <present/absent>, <n> functions defined, execution order <in-order/out-of-order>
- target rung: <1|2|3>, based on <stated usage pattern>
- blockers to promotion: <specific list, or "none">
```

If the notebook is rung-1-appropriate (true one-off), say so and stop — don't apply rung-2/3 discipline to something that's already at its correct maturity level.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
