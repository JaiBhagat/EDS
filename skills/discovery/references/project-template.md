# PROJECT.md template

The project operating manual. Discovery Stage 6 emits this alongside the Brief.
Tells any future session how to work in THIS project specifically.

```markdown
# Project: <name>

## Data access
Where the data lives, how to load it, credentials/roles needed.
- Source 1: <path or connection string> — <how to read it>
- Source 2: ...

## Environment
- Python version: <version>
- Key packages: <list>
- Compute constraints: <memory, GPU, time limits>
- Seed policy: always set `random_state=42` unless exploring variance

## How to run
- Probes: `python skills/discovery/scripts/probes/<probe>.py <args>`
- Funnel: `python skills/fde/scripts/evaluators/funnel.py`
- Baselines: `python skills/baseline-first/scripts/baselines.py <args>`
- Gates: `python scripts/gates/gate_<stage>.py .`
- Audit: `python scripts/eds_audit.py .`

## Conventions
- Sample size for EDA: <N rows>
- Date column: <col> — all time-based splits use this
- Entity column: <col> — used for entity-grouped splits
- Target: <col> — defined in BRIEF.md

## .eds/ layout
```
.eds/
├── BRIEF.md          # problem contract + Plan
├── PROJECT.md        # this file
├── progress.md       # session handoff notes
├── data-manifest.json
├── verification/     # gate outputs
├── activity.log      # append-only event log
├── holdout_ledger.json
├── features/         # FDE catalog + journal
├── models/           # MDE experiments, contract, champion
└── debt-ledger.md
```

## Notes
<project-specific notes, gotchas, domain knowledge>
```
