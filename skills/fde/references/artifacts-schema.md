# FDE artifacts — schemas

All under `.eds/features/` in the project that installs this plugin. Context-loading rule is strict: only `feature_catalog.json` and the current round's `candidate_features.md` load into context by default; `feature_journal.md` and `experiment_log.md` are grepped on disk, never bulk-loaded — this is what keeps a thousand-feature campaign inside a real context window.

## `feature_catalog.json` — machine-readable, loaded

Array of entries:

```json
{
  "name": "user_txn_count_7d",
  "family": "frequency",
  "hypothesis_id": "H-014",
  "code_ref": "scripts/features/user_txn_count_7d.py::compute",
  "construction_hash": "a1b2c3d4e5f6",
  "data_version": "2026-07-01",
  "availability": "point-in-time at decision_ts, 7d trailing window",
  "cost": 1,
  "online_available": true,
  "status": "candidate | selected | rejected | evicted",
  "sessions_open": 2,
  "evidence": "stage 4 corr 0.18, stage 6 importance 0.09, stage 7 rank-stable"
}
```

`status` transitions: `candidate` → `selected` (survived through stage 10) or `rejected`/`evicted` (failed a stage — record which one in `evidence`). `sessions_open` increments once per Stop hook run while `status: candidate`; the Stop hook flags entries open past `MAX_CANDIDATE_SESSIONS` sessions as pruning candidates.

## `feature_journal.md` — append-only, grepped not loaded

One entry per hypothesis outcome, eviction, holdout touch, or stop decision:

```
## 2026-07-11
- [new] `user_txn_count_7d` (frequency) — status: candidate, hypothesis: H-014
- [evicted] `user_avg_amt_alltime` — stage 0: computed over full table including future rows, leakage
- [holdout touch] campaign `churn-2026-q3`, touch 1/1, confirmation AUC 0.812
- [stop] campaign `churn-2026-q3` — marginal-gain floor: best candidate lift 0.003 < cross-fold SE 0.006
```

## `candidate_features.md` — current round only

Live candidates for the round in progress: hypothesis link, construction summary, current funnel position. Overwritten each round, not append-only.

## `selected_features.md` — compact, loaded

Human-readable list of the chosen set: definition, rationale (one line, pointing at the hypothesis + evidence), owner. This is what `baseline-first` and downstream modeling read — never the full catalog.

## `feature_evaluation.md` — current round only

Funnel results per round, per stage: how many candidates entered, how many survived, why the rest were evicted. Overwritten each round; the journal keeps the durable summary line.

## `experiment_log.md` — round-level, grepped not loaded

Config, folds, budgets consumed, metric trajectory per round. Detail lives here; the journal gets one summary line per round.
