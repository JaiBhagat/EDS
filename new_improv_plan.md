# EDS — P4 Remediation Plan
### Closing the evaluation gaps and lifting every dimension score

**Baseline:** `82fd92c` (P3 close-out)
**Scope:** the seven defects in the evaluation report, re-cut into four executable phases.
**Written to be handed to Claude Code and executed top-to-bottom.** Every task has a file path and a testable exit criterion. Nothing here is speculative work.

---

## 0. Score targets

| Dimension | Now | Target | Closed by |
|---|---|---|---|
| Architecture & design | 9 | 9 | — (no change needed) |
| Ponytail ideology fidelity | 7 | **9** | P2 + P3 |
| ECC structural fidelity | 9 | 9 | — |
| Implementation correctness | 7 | **9** | P0 + P1 |
| Engineering hygiene | 4 | **9** | P0 |
| Evidence / proof of claim | 3 | **8** | P2 |
| DS lifecycle coverage | 8 | **9** | P4 (optional) |

The two that move the most — hygiene and evidence — are also the two cheapest. That is the whole shape of this plan.

---

## 1. The benchmarking decision (settled, so the plan can be written)

The `benchmarks/` directory is **not model benchmarking**. It never was. Two different things share the word:

| | Model benchmarking | Plugin benchmarking (`benchmarks/`) |
|---|---|---|
| Question | "Is 0.71 AUC good for *this* business problem?" | "Does the agent notice `account_closed_reason` is a leak?" |
| Needs | Stakeholders, prior model, business bar | A synthetic CSV you generated at seed 7 |
| Automatable | **No** — and EDS correctly doesn't try. It's the Brief's `baseline bar` field, supplied by the user, enforced by `evaluation-design`. Already solved. | **Yes** — the answer key is five defects you planted yourself. |
| Verdict | Out of scope, by design, correctly | **In scope, and mandatory** |

So the objection is right about model benchmarking and doesn't apply to the thing that's broken. But the *ambition* of the current benchmark harness (3 arms × 6 tasks × n reps, token/cost/LOC metrics, LLM-judged ladder adherence) is genuinely over-built and genuinely expensive. That is what gets cut.

**The split that resolves it:**

- **Proof of function** — *does EDS's machinery actually catch the planted defects?* Four of the five defects can be checked **with no LLM at all**: run `split_overlap.py` on the fixture splits, run the grain check on `orders.csv`, run `ds-lint` on `model_dev.ipynb`, run the leakage scan on `features.csv`. Deterministic, free, fast, runs in CI on every push. **This is not a benchmark — it is an integration test wearing a benchmark's clothes.** Mandatory. Phase P2a.
- **Proof of value** — *does an agent with EDS beat an agent without it?* Needs a real LLM, costs money, is noisy across reps. **Descope hard:** one headline run, 6 tasks × 2 arms (eds / no-eds) × 2 reps, graded by hand against `_answer-key.md`, one table in the README, done once, never in CI. Optional. Phase P2b.

**Non-negotiable either way:** delete `benchmarks/results/`. Twelve zero-byte `status.txt` and `diff.patch` files that look like a run happened are worse than an empty directory — a reader who opens them concludes the author manufactures evidence. Replace with a `results/README.md` stating exactly what has and hasn't been run. Honest absence beats fake presence, and it's the ponytail move.

---

## P0 — Stop the bleeding (½ day)
> *Hygiene 4 → 9, Correctness 7 → 8. Do this first; it's an afternoon and it removes every embarrassing thing in the repo.*

### P0.1 — Fix the live crash
**File:** `skills/fde/scripts/evaluators/funnel.py:200`

```python
# before — np.array_split on a DataFrame returns object ndarrays on numpy 2.x
slices = np.array_split(df_sorted, n_slices)

# after — split the index, slice with .iloc
slices = [df_sorted.iloc[idx] for idx in np.array_split(np.arange(len(df_sorted)), n_slices)]
```
**Exit:** `pytest tests/test_funnel.py` → 15/15 pass on pandas 3.x.

### P0.2 — Pin the environment
**New file:** `requirements.txt` (or `pyproject.toml` — pick one, don't ship both)
```
pandas>=2.0,<4.0
numpy>=1.24,<3.0
scikit-learn>=1.3
pytest>=8.0
```
Then add a `## Requirements` line to `README.md`.
**Exit:** a fresh venv from `requirements.txt` runs the full suite green.
**Why it's non-optional:** never-cut item 5 says *"environment pinned."* The plugin currently doesn't pin its own. This is the single most quotable inconsistency in the repo.

### P0.3 — CI actually runs the tests
**File:** `.github/workflows/ci.yml` (rename/extend `check-rule-copies.yml`)
```yaml
name: ci
on: [push, pull_request]
jobs:
  rules:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: node scripts/check-rule-copies.js
  tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.11", "3.12"]
        pandas: ["2.2.*", "3.0.*"]      # the matrix that would have caught P0.1
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python }}" }
      - run: pip install -r requirements.txt "pandas==${{ matrix.pandas }}"
      - run: pytest -q
```
**Exit:** a PR with a deliberately broken test goes red.

### P0.4 — Untrack local state
```bash
git rm -r --cached .tokensave .claude .eds __pycache__ \
  $(git ls-files | grep -E '\.pyc$|\.DS_Store$') 
git commit -m "chore: untrack local state and build artifacts"
```
Also add `new_improv_plan.md` to `plugin.json`'s `exclude` list (or move working plans to `docs/plans/`).
**Exit:** `git ls-files | grep -E 'tokensave|DS_Store|\.pyc|settings.local'` returns nothing.
**Why it matters:** the repo currently ships a 1.3 MB SQLite code index and your home directory path to anyone who clones it.

---

## P1 — Make the harness fail closed (1–2 days)
> *Correctness 8 → 9, Ponytail +1. A verification harness that fails open is worse than no harness — it manufactures confidence.*

### P1.1 — One canonical stage list
**New file:** `scripts/lib/stages.py` + `hooks/scripts/lib/stages.js` (or a single `stages.json` both read — preferred, single-source, same pattern as the rule text).

```json
{
  "stages": [
    {"id": "discovery",              "skill": "discovery",              "gate": "gate_discovery.py",              "surface": ["BRIEF.md", ".eds/"]},
    {"id": "data-audit",             "skill": "data-audit",             "gate": "gate_data_audit.py",             "surface": [".eds/data-manifest", "audit"]},
    {"id": "eda",                    "skill": "eda-workflow",           "gate": "gate_eda.py",                    "surface": ["eda", "*.ipynb", "plots/"]},
    {"id": "label-design",           "skill": "label-design",           "gate": "user-signoff",                   "surface": ["label", "target"]},
    {"id": "evaluation-contract",    "skill": "evaluation-design",      "gate": "user-signoff",                   "surface": [".eds/models/validation_contract.json"]},
    {"id": "fde",                    "skill": "fde",                    "gate": "gate_fde.py",                    "surface": [".eds/features/", "feature", "funnel"]},
    {"id": "baseline",               "skill": "baseline-first",         "gate": "gate_model.py",                  "surface": ["baseline", ".eds/models/"]},
    {"id": "model",                  "skill": "mde",                    "gate": "gate_model.py",                  "surface": [".eds/models/", "train_", "experiment"]},
    {"id": "calibration",            "skill": "mde",                    "gate": "gate_model.py",                  "surface": ["calibrat", ".eds/models/"]},
    {"id": "decision-optimization",  "skill": "decision-optimization",  "gate": "gate_decision_optimization.py",  "surface": ["threshold", "cutoff"]},
    {"id": "report",                 "skill": "ds-reporting",           "gate": "gate_report.py",                 "surface": ["report", "findings"]},
    {"id": "monitoring-handoff",     "skill": "model-monitoring",       "gate": "gate_model.py",                  "surface": ["monitor", "drift", "psi"]}
  ]
}
```
Kills three bugs at once: the schema's `audit` vs ds-lint's `data-audit` mismatch (currently → **no scope guard during the first working stage**), the four stages with no gate script, and the drift between README / brief-schema / `STAGE_SURFACE_MAP`. Stages whose gate is `user-signoff` are now *explicitly* signoff-gated rather than silently ungated.

**Consumers to rewire:** `hooks/scripts/ds-lint.js` (`STAGE_SURFACE_MAP`), `scripts/state/plan.py`, `scripts/eds_audit.py`, `skills/discovery/references/brief-schema.md` (Plan template), `README.md`.

**Exit:** a test asserts `set(stages.json) == set(STAGE_SURFACE_MAP) == set(brief-schema Plan template) == set(gates on disk ∪ {user-signoff})`. Drift becomes a CI failure, exactly like rule-text drift already is.

### P1.2 — Unknown stage = fail closed
**File:** `hooks/scripts/ds-lint.js:287`
```js
const patterns = STAGE_SURFACE_MAP[currentStage];
if (!patterns) return findings;          // ← silently gives up
```
→ emit a finding: `unknown stage "<x>" — not in stages.json; scope guard cannot run`. An unrecognised stage is a *bug*, not a free pass.

### P1.3 — Unparseable Plan = FAIL, not PASS
**File:** `scripts/eds_audit.py`
Currently a Plan the parser can't read reports `[PASS] done-stages-gated — no done stages yet`. Distinguish three states: **no Plan section** (fail: discovery incomplete) / **Plan present, 0 entries parsed** (fail: malformed) / **Plan parsed, 0 done** (pass).
**Exit:** `test_observability.py` gains a case feeding a table-formatted Plan → audit returns FAIL with `plan-unparseable`.

### P1.4 — Align the test fixture with the schema
`tests/fixtures/eds_fixture/.eds/BRIEF.md` uses a markdown-table Plan; `brief-schema.md` mandates `- stage · skill · status · gate` bullets. The fixture is currently testing a format the product doesn't emit. Rewrite the fixture to the canonical format — and *keep* a table-format fixture as the **negative** case for P1.3.

### P1.5 — Tighten `join-no-assert`
**File:** `hooks/scripts/ds-lint.js:120` — the window test `/(assert|\.shape|len\(|COUNT\()/i` is satisfied by the word "un**assert**ed" in a comment. Require an assertion *statement* (`^\s*assert\b`, or `.shape` / `len(` in an executable line), and strip comments before testing the window.
**Exit:** a test where the only "assert" is inside a `#` comment still produces the finding.

---

## P2 — Evidence (2 days, split into mandatory + optional)
> *Evidence 3 → 8. This is the phase that decides whether the repo is credible to a stranger.*

### P2a — Proof of function (MANDATORY, no LLM, runs in CI)
**New file:** `tests/test_fixture_defects.py`

The fixture already has five planted defects and `_answer-key.md` already states them precisely. Assert that **EDS's own machinery catches each one** — no agent, no API key, no arms, no cost:

| Defect | Assertion | Component under test |
|---|---|---|
| 1. 216 duplicate `order_id`s | grain/dup check on `orders.csv` reports ≥1 duplicate-key violation | `data-audit` scripts |
| 2. `account_closed_reason` leak | leakage scan on `features.csv` vs `users.churned` flags the column | `leakage-check/scripts/feature_availability_scan.py` |
| 3. ~10% `user_id` overlap train/test | `split_overlap.py` reports non-zero entity overlap | `leakage-check/scripts/split_overlap.py` |
| 4. `KFold(shuffle=True)` on time data | `ds-lint` on `notebooks/model_dev.ipynb` emits `time-shuffle` | `hooks/scripts/ds-lint.js` |
| 5. Bare accuracy on 19% base rate | `validation_contract create` on the fixture proposes a non-accuracy metric, or flags accuracy-with-no-baseline | `mde/scripts/validation_contract.py` |

This is the strongest possible evidence *and* the cheapest: it's deterministic, it costs nothing, it runs on every push, and it never goes stale. If any of the five stops firing, CI goes red. **This alone takes Evidence from 3 to ~7.**

**Exit:** `pytest tests/test_fixture_defects.py` → 5 passed, wired into P0.3's CI job.

### P2b — Proof of value (OPTIONAL, one-shot, hand-graded)
Only if you want a headline number in the README. Descoped from the original ambition:

- **Cut:** 3 arms → **2** (eds / no-eds; drop `terse`, it answers a question nobody asked). 6 tasks × 2 reps = 24 sessions. Drop token/cost/LOC metrics entirely; drop the promptfoo single-shot arm.
- **Keep:** one number — **pitfall catch rate** = (defects detected or flagged) / (defects the task touches), per arm, from `_answer-key.md`.
- **Output:** one table in `README.md`, plus `benchmarks/results/README.md` recording model id, date, and n. Run once. Never in CI.
- **Task 06 is the one worth the money** — the no-go trap. "Does the agent build a classifier for something `events.csv` already logs directly, or does it correctly refuse?" That single row proves the ladder does something a generic agent doesn't. If you only run one task, run that one.

### P2c — Delete the fake evidence (MANDATORY, 5 minutes)
```bash
git rm -r benchmarks/results/
```
Replace with `benchmarks/results/README.md`:
> No agentic benchmark run has been completed yet. `tests/test_fixture_defects.py` provides deterministic proof that the plugin's checks catch all five planted defects. A comparative eds/no-eds run is tracked as `# eds: deferred — proof-of-value benchmark, see P2b`.

Twelve 0-byte files that look like results are a credibility liability. An honest "not yet run" is not.

---

## P3 — Ponytail cleanup (½ day)
> *Ponytail 7 → 9.*

### P3.1 — Unpollute the debt ledger
**File:** `hooks/scripts/harvest-debt.js`
- Exclude `tests/`, `benchmarks/fixtures/`, and `**/__pycache__` from the scan (7 of ~10 current ledger entries are captured from `test_harvest_debt.py`'s own fixtures).
- Trim capture at the end of the reason, not end-of-line — the ledger currently holds entries like `` — skipping cross-validation for speed\nprint(1)\n") ``.
- **Exit:** a test asserting a marker inside `tests/` is *not* harvested, and a marker followed by trailing code captures only the reason. Then clear and re-harvest the ledger.

**Why this matters more than it looks:** `/evolve` clusters the ledger to find recurring shortcuts. A ledger that is 70% noise means the continuous-learning loop — the ECC pattern the repo explicitly claims — is dead on arrival.

### P3.2 — Seed the ledger honestly
Everything this plan *chooses not to do* gets a marker. Deferring inside the ideology is not a cut; deferring silently is:
```
# eds: deferred — proof-of-value benchmark (eds vs no-eds arms), P2b, needs API budget
# eds: deferred — fairness/adverse-action skill, P4.1
# eds: deferred — unsupervised/segmentation lifecycle path, no Plan template exists
# eds: deferred — serving latency/cost check in model-handoff (axiom 6 arguably demands it)
```

### P3.3 — README truth-up
- Add the three missing skills to the architecture tree: **explainability, model-handoff, notebook-assembly**.
- `82 tests across 6 files` → **96 across 7** (make it `pytest --collect-only -q | tail -1`, or just drop the number — a number that drifts is worse than no number).
- `EDS.md (68 lines)` → **87**.
- Add an explicit **"Not in scope (v0.1)"** section: deep learning, NLP/LLM eval, unsupervised, recommender, data ingestion. Declared scope reads as judgment; undeclared scope reads as an oversight.

---

## P4 — Coverage (optional, 1–2 days)
> *Coverage 8 → 9. Do this when P0–P3 are green, not before.*

### P4.1 — `fairness` skill into **core**, not the pack
The biggest real gap. There is a `credit-risk` domain pack and no disparate-impact / proxy-variable / adverse-action-reason-code skill. In BFSI that is the regulator's first question, and it's your own domain — you'd feel this absence on your first real use. Minimum viable: group-wise metric parity table, proxy-variable correlation scan against protected attributes, reason-code export from the existing `explainability` skill. It slots naturally as a gate before `decision-optimization` (you cannot set a threshold you can't defend).

### P4.2 — Two smaller holes, if cheap
- **Class imbalance / sampling** — currently implicit inside MDE; deserves a named decision point (resample vs class-weight vs threshold-move).
- **Missing-data strategy** — audit *detects* nulls; nothing owns the *decision* (MAR/MNAR, imputation choice, missingness-as-signal).

---

## Sequence and exit criteria

| Phase | Effort | Gate to move on | Status |
|---|---|---|---|
| **P0** | ½ day | CI green on a 2×2 python/pandas matrix; `git ls-files` clean; funnel test passes | **DONE** |
| **P1** | 1–2 days | One `stages.json`; drift test in CI; every guard fails closed; malformed Plan → FAIL | **DONE** |
| **P2a** | 1 day | `test_fixture_defects.py` → 7/7, in CI. **`results/` deleted.** | **DONE** |
| **P2b** | optional | 2-arm table in README, or a deferred marker. Either is honest; silence is not. | deferred marker placed |
| **P3** | ½ day | Ledger clean; `/evolve` runs on real signal; README matches reality | **DONE** |
| **P4** | optional | Fairness skill shipped in core | deferred marker placed |

**Total to hit every target score except Coverage: ~3–4 days.**

---

## The one thing to take away

Every remaining defect in EDS is a case of the plugin **not doing to itself what it demands of its users**: it insists on pinned environments and has none; it insists on verification gates and its own gates fail open; it insists that skipped work gets a marker and its marker ledger is full of test noise; it insists on honest evidence and ships twelve empty files where results should be.

Fix that asymmetry and the ideology stops being something the README claims and becomes something the repo demonstrates. That is the whole plan.