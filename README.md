# EDS — Everything Data Science

A first-principles, domain-agnostic data science plugin for Claude Code. Six axioms, a cost-weighted ladder, and a never-cut list govern every skill: analysis serves a decision, the data is guilty until proven innocent, the baseline is the burden of proof, time flows one way, if it can't be reproduced it didn't happen, models exist to improve operational decisions not predictive metrics.

## Requirements

```bash
pip install -r requirements.txt
```

Tested on Python 3.11–3.12 with pandas 2.2.x and 3.0.x.

## Install

```bash
claude plugin add <path-to-this-directory>
```

Or from the marketplace:

```bash
/plugin marketplace add eds
```

Verify it loaded:

```bash
claude plugin list   # should show eds ✔
```

## Using EDS on any data science problem

EDS works as a senior data scientist that drives the full lifecycle — you bring the data and the business question, EDS handles the sequence. Here's how a typical project runs:

### 1. Start with discovery

Open your project directory (where the data lives) and describe the problem:

```
"We have customer transaction data and want to predict churn"
"Should we build a model to detect fraud in these claims?"
"Analyze whether the new checkout flow improved conversion"
```

EDS runs the Discovery Loop — asks about the decision, cost of being wrong, data inventory — and produces three artifacts:

- **`.eds/BRIEF.md`** — the problem contract with a lifecycle Plan
- **`.eds/PROJECT.md`** — how to work in THIS project (data access, environment, conventions)
- **`CLAUDE.md`** (at project root) — behavioral guardrails for LLM-assisted DS work: think-before-coding, simplicity-first, audit-before-analyze, baseline-before-complex, reproducibility, anti-patterns. Works standalone — even without the EDS plugin loaded, the project's `CLAUDE.md` enforces DS discipline. If a `CLAUDE.md` already exists, EDS appends the DS-specific sections without overwriting your existing guidelines.

### 2. Let the Plan drive

Once the Brief is confirmed, EDS drives the pipeline stage by stage without hand-holding:

```
audit → eda → label-design → evaluation-contract → fde → baseline → model →
calibration → decision-optimization → report → monitoring-handoff
```

Each stage completes, passes its verification gate, and the agent proceeds to the next. It pauses only at genuine decision gates (label definition, evaluation contract, champion acceptance) where your input is needed.

### 3. Key commands

| Command | What it does |
|---|---|
| `/eds:discover` | Start or resume the Discovery Loop |
| `/eds:brief` | Show the current Problem Brief |
| `/eds:features` | Start or resume a feature discovery campaign |
| `/eds:eds lite\|full\|ultra\|off` | Switch mode |
| `/eds:eds-review` | Review a diff for rigor gaps and over-engineering |
| `/eds:eds-debt` | Review deferred-work markers |
| `/eds:eds-audit` | Run the five-subsystem harness health check |

### 4. What EDS enforces automatically

These fire without you asking — they're hooks, not commands:

- **Session start**: Loads your Brief, Plan status, and mode. Flags stale data sources.
- **Every code edit**: Catches leakage (fit-before-split, time-shuffled CV), missing seeds, unasserted joins, eval-on-train — all mapped to the specific axiom violated.
- **Session end**: Harvests deferred markers into the debt ledger, syncs feature journal, checks state consistency.
- **Stage completion**: No stage can be marked "done" without a passing verification gate. The `ds-lint` hook blocks it.
- **Scope guard**: Writing to files outside the current stage's surface triggers a warning — one stage at a time.

### 5. The verification gates

Every Plan stage has a gate that must pass before it's marked done:

```bash
python scripts/gates/gate_discovery.py .     # Brief complete, confirmed, Plan present
python scripts/gates/gate_data_audit.py .    # Manifest written, sources profiled
python scripts/gates/gate_eda.py .           # Findings backed by evidence
python scripts/gates/gate_fde.py .           # Funnel trail, catalog-journal reconciled
python scripts/gates/gate_model.py .         # Experiment log, contract hash, holdout discipline
python scripts/gates/gate_decision_optimization.py .  # Cites calibration + capacity
python scripts/gates/gate_report.py .        # Every number traces to an evidence path
```

Gate results are written to `.eds/verification/` and logged to `.eds/activity.log`.

### 6. Modes

- **lite** — advisory only, never blocks, warnings instead of hard requirements
- **full** (default) — ladder enforced, never-cut items are hard requirements, deferred markers required
- **ultra** — audit posture on every touch, reviewer agents auto-invoked on model diffs
- **off** — plugin stays silent, skills still invocable manually

### 7. Working across sessions

Kill a session mid-work and come back later — EDS picks up where you left off:

- The Plan in `.eds/BRIEF.md` tracks which stages are done/pending
- `.eds/progress.md` records handoff notes with resume points
- `.eds/data-manifest.json` detects when data has changed between sessions
- The session-start hook reports the full status on every open

### 8. Domain and method packs

Optional extensions for specific domains or methods:

```bash
# Install with specific packs
bash install.sh --profile core --with methods:time-series,domains:credit-risk
```

Available: `time-series`, `causal-inference`, `credit-risk`, `marketing-analytics`, `feature-lifecycle`, `data-contracts`, `mlops-deployment`, `model-governance`.

## Architecture

```
.claude-plugin/plugin.json    # plugin manifest
EDS.md                        # always-on ruleset (103 lines)
skills/
  eds-core/                   # ladder + axioms + delegation map
  discovery/                  # 7-stage Discovery Loop + 6 probes
  data-audit/                 # grain, nulls, dupes, ranges, joins
  eda-workflow/               # question-driven EDA
  fde/                        # Feature Discovery Engine (16 hypothesis families, 11-stage funnel)
  mde/                        # Model Discovery Engine (diagnosis → candidates → champion)
  baseline-first/             # rung 5-6 before rung 8
  evaluation-design/          # metric + split + baseline comparison
  label-design/               # delayed/proxy/weak labels
  leakage-check/              # temporal, target, entity leakage
  decision-optimization/      # thresholds from calibrated scores + capacity
  error-analysis/             # slice-based error diagnosis
  experiment-design/          # A/B test sizing + guardrails
  model-monitoring/           # PSI drift + operational decay
  ds-reporting/               # decision-first report structure
  notebook-hygiene/           # notebook → script maturity ladder
  explainability/             # feature importance + SHAP explanations
  model-handoff/              # production readiness checklist
  notebook-assembly/          # notebook → deliverable construction
commands/                     # thin shims: /discover, /brief, /eds-review, /eds-audit, etc.
agents/                       # data-auditor, leakage-hunter, eval-designer, stats-skeptic,
                              # ds-code-reviewer, repro-checker, feature-scientist, model-scientist
hooks/
  scripts/
    session-start.js          # context injection (Brief, Plan status, mode)
    ds-lint.js                # 7 code checks + H3 gate enforcement + H4 scope guard
    harvest-debt.js           # deferred-marker harvest on Stop
    feature-journal-sync.js   # FDE catalog diff on Stop
    session-wrap.js           # state consistency check on Stop
scripts/
  gates/                      # 7 verification gate runners (gate_discovery.py, etc.)
  state/                      # manifest.py, plan.py, progress.py
  eds_init.py                 # full session init (env + manifest + state reconciliation)
  eds_audit.py                # 5-subsystem harness auditor
  activity_log.py             # append-only event log utility
tests/                        # 110 tests across 9 files
benchmarks/                   # 6 tasks, ecommerce fixture with planted defects
rules/common/                 # rigor, reproducibility, communication
skills-packs/                 # optional domain + method packs
```

## The `.eds/` directory (in your project)

When EDS works on a data project, it creates `.eds/` in the project root:

```
.eds/
├── BRIEF.md                  # problem contract + Plan
├── PROJECT.md                # project operating manual
├── progress.md               # session handoff notes
├── data-manifest.json        # source hashes, row counts, freshness
├── verification/             # gate pass/fail records
├── activity.log              # append-only event log
├── holdout_ledger.json       # confirmation holdout touches (shared FDE/MDE)
├── features/                 # FDE catalog, journal, rounds
├── models/                   # MDE experiments, validation contract, champion
└── debt-ledger.md            # harvested deferred markers
```

This directory belongs to the project, not the plugin. Commit it to version control.

## Not in scope (v0.1)

EDS covers supervised prediction, classification, regression, and structured analytics end-to-end. The following are deliberate omissions, not oversights:

- Deep learning / neural architecture search
- NLP / LLM evaluation (BLEU, perplexity, etc.)
- Unsupervised learning / segmentation
- Recommender systems
- Data ingestion / ETL orchestration
- Fairness / adverse-action auditing (tracked as deferred — highest-priority gap for v0.2)

## Contributing

Single-source rule text: edit `EDS.md` and `rules/common/*.md`, then run `node scripts/generate-adapters.js` to update the Cursor/Copilot/AGENTS.md copies. The CI check (`scripts/check-rule-copies.js`) will fail on drift.

Skills are independent — each is a self-contained `SKILL.md` + optional `scripts/`. Adding a new skill doesn't require touching any other skill. Adding a new gate requires a new `scripts/gates/gate_<stage>.py` and a matching entry in the Plan template.

## License

MIT
