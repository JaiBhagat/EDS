---
name: notebook-assembly
description: >
  Generates a reproducible notebook from the Plan table and .eds/ artifacts
  — one cell per completed Plan stage, each cell's markdown header quoting
  its gate record. Never freehand the final notebook — assemble it. Use
  after all modeling stages are complete (champion selected, calibrated,
  threshold set, bundle saved). The assembled notebook is the deliverable
  for "pre-production" — later modularization is mechanical from here.
  Automatically runs notebook-hygiene's maturity_check.py on output and
  fails assembly if rung-2 blockers exist.
argument-hint: "[--brief-path .eds/BRIEF.md] [--out notebook.ipynb]"
license: MIT
---

# Notebook Assembly

The notebook is a *derived artifact*, not a primary one. It's assembled from what was actually executed and verified, not freehanded from memory of a session.

## Why assemble instead of write

1. **Fidelity** — each cell maps 1:1 to a Plan stage with a passing gate record
2. **Regenerable** — if a stage is redone, re-run assembly and the notebook updates
3. **Auditable** — gate record references in markdown headers prove what was verified
4. **Hygiene** — maturity_check runs automatically; rung-2 blockers fail the build

## Prerequisites

1. `.eds/BRIEF.md` exists with a Plan table
2. Plan stages are marked `done` with gate-record references
3. `.eds/verification/` contains passing gate records for each stage
4. `.eds/models/bundle/` exists (model-handoff complete)

## Assembly process

1. **Parse the Plan table** from `.eds/BRIEF.md` — extract stage names, status, gate refs
2. **For each completed stage**, generate:
   - A markdown cell with: stage name, gate record reference, key findings
   - A code cell with the reproducible code for that stage (from gate artifacts)
3. **Prepend setup cells**: imports, seed, data path, environment check
4. **Append results cells**: champion summary, threshold analysis, final metrics with CI
5. **Run maturity_check** on the generated notebook
6. **Output** the notebook to the project root

## Usage

```
python skills/notebook-assembly/scripts/assemble_notebook.py \
    --brief-path .eds/BRIEF.md \
    --out <project_name>.ipynb
```

## Maturity gate

After assembly, the script invokes `notebook-hygiene`'s maturity_check:
- Rung-2 blockers (hardcoded paths, no seed cell, no reproducibility header) = FAIL
- Rung-1 warnings = WARN but pass

A failed maturity check means the notebook is not shippable — fix the blocker and re-assemble.

## Boundaries

- This skill GENERATES the notebook — it does not execute it
- Code cells are assembled from artifacts and session records, not invented
- If a stage has no gate record, it's excluded with a `# eds: deferred` marker
- The assembled notebook imports from `features.py` and `inference.py` if they exist (P1.1/P1.5)

## Handoff contract

On completing: (1) mark notebook-assembly Plan entry `done`, (2) state the maturity check result, (3) if all Plan stages are done, proceed to `ds-reporting` for the stakeholder summary.
