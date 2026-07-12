# EDS Plugin — Improvement Plan
**Basis:** the Working Review (previous report) + a second pass over the repo source (`baselines.py`, `time_coverage.py`, hooks, gates, `ds-reporting`, fde scripts).
**Organizing principle:** your end goal is a *solid pre-production notebook* per project — data audit → EDA (confidence-holding) → FE → model → calibration → threshold → **saved model** → **assembled notebook** — that later converts mechanically to modules. Every item below is prioritized against that goal.

---

## P0 — Correctness fixes (do before the next project run)

These are the bugs that produce silently wrong or mislabeled numbers. ~1 day of work total.

### P0.1 Metric plumbing: one metric, declared once, used everywhere
The single biggest source of friction in the fraud run. Three scripts each handle metrics independently and disagree:

| Script | Current behavior | Fix |
|---|---|---|
| `mde/scripts/validation_contract.py` | `--metric auto` → silently `roc_auc` for classification; never reads the Brief | On `create`, parse `.eds/BRIEF.md` Stage 5 "Primary metric" and use it; if a Brief exists with an explicit metric and the user passes nothing, **that metric wins**. Error loudly (don't fall back) if the Brief metric doesn't map to a known scorer. |
| `baseline-first/scripts/baselines.py` | **No `--metric` flag at all**; `roc_auc_score` hardcoded; LR fitted without `class_weight` | Add `--metric {roc_auc,average_precision,f1,neg_rmse,...}` mapped to sklearn scorers, defaulting to the contract/Brief value if `.eds/models/validation_contract.json` exists. Add `--class-weight balanced` support. Report the trivial baseline in the same metric (all-zeros AUPRC = base rate), not "AUC=0.5". |
| `mde/scripts/experiment_log.py` / `champion_selection.py` | Log whatever `metric_name` is passed; contract mislabel propagates | Once P0.1a lands this fixes itself, but add a validation: `log` should refuse an entry whose `metric_name` ≠ contract metric (or require an explicit `--override-metric` with a reason string that gets stored). |

Also make the default imbalance-aware: when creating a contract for classification, read the target's positive rate (the target-profile probe already computes it); below ~2% positives, default to `average_precision` instead of `roc_auc`, and say why in `metric_reason`.

### P0.2 `calibration.py fix` — remove the self-split footgun
Current: splits *whatever file it's handed* 70/30 to fit and score the calibrator → fit isotonic on ~52 fraud rows of the test set in your run, collapsing AUPRC 0.81→0.59.

New interface (breaking change, intentionally):
```
python calibration.py fix \
    --fit-path cal_predictions.csv   # predictions on a held-out CAL split (from train side)
    --apply-path test_predictions.csv \
    --y-true <col> --y-prob <col> --method platt|isotonic
```
Plus two guardrails inside the script:
- Refuse isotonic when the fit set has < ~200 positives (isotonic needs density; recommend Platt below that and say so).
- After applying, recompute AUPRC on the apply set and **warn loudly if rank-order changed** (AUPRC before vs after should be ≈ equal for monotone calibration; a drop means something is wrong). This single assertion would have caught the bug automatically in your run.

Correspondingly, the MDE SKILL.md workflow must instruct carving a calibration slice out of *train* (e.g., last 10–15% of train by time for temporal splits) at split time — right now no stage ever creates a cal split, which is why the tool got pointed at test.

### P0.3 `time_coverage.py` — handle relative/numeric time columns
Current: `pd.to_datetime` on the fraud data's `Time` (seconds elapsed) parses as nanoseconds-since-epoch → "coverage: 1970-01-01 → 1970-01-01 (0 days)", which is noise. Fix: detect numeric columns whose plausible datetime parse collapses to a single 1970 date; in that case treat the column as **elapsed time** — report span in seconds/hours, monotonicity, and per-bin volume (the useful analysis the assistant had to hand-roll). Add `--unit s|ms|epoch|auto`.

---

## P1 — Close the loop to your stated end-state (the missing features)

These aren't bugs — they're capabilities the plugin *doesn't have* that your goal requires. This is where most of the new value is.

### P1.1 NEW SKILL: `model-handoff` (save the model, properly)
Nothing in the pipeline serializes a model. `champion.json` stores metadata only; the actual fitted LR, the Platt calibrator, the feature list, and the chosen threshold from your fraud run live nowhere — rerun the notebook or lose them. For "pre-production," the deliverable must be a loadable bundle:

```
.eds/models/bundle/
  model.joblib            # fitted estimator
  calibrator.joblib       # fitted calibrator (or None)
  feature_spec.json       # ordered feature list + dtypes + engineered-feature formulas
  threshold.json          # operating threshold(s) + tier map + cost assumptions
  metrics.json            # holdout metrics + bootstrap CI (see P1.3)
  inference.py            # generated: load bundle, score a dataframe end-to-end
  MANIFEST.json           # hashes of all of the above + contract hash + seed + package versions
```
The generated `inference.py` (raw df → engineered features → calibrated score → tier) is what makes later modularization mechanical — the feature-engineering logic gets written down *once, as code*, instead of living scattered across notebook cells. Gate: `MANIFEST` hash recorded in the Brief's Plan row.

### P1.2 NEW SKILL: `notebook-assembly` (generate, don't freehand, the final notebook)
In your run the assistant wrote `fraud_detection.ipynb` from memory of the session — it happened to be good, but nothing guarantees it matches what was actually executed, and nothing regenerates it if a stage is redone. Build an assembler that walks the Plan table + `.eds/` artifacts (gate records, feature journal, experiment log, champion, calibration report, threshold analysis) and emits the notebook with one cell per completed Plan stage, each cell's markdown header quoting its gate record. Then automatically run `notebook-hygiene`'s `maturity_check.py` on the output and fail assembly if rung-2 blockers exist (hardcoded paths, no seed cell). Result: notebook stage ↔ Plan row ↔ future module, guaranteed in lockstep — exactly your "solid notebook now, modular later" path.

### P1.3 NEW SCRIPT: `bootstrap_ci.py` (shared utility, wired into ds-reporting)
The fraud report asserted "plausibly 0.75–0.87 AUPRC" without computing it — on 75 positives that range is the difference between a credible report and a hand-wave. One small script (resample the holdout with replacement, recompute the primary metric, report the 90% interval; stratified resampling so every draw has positives), used in three places: baseline bar (is LR really above the heuristic?), champion vs. bar (did features *really* add +0.053?), and the final report's headline number. Make `ds-reporting`'s SKILL.md require a computed interval for any metric whose positive count < ~500. Cheap, and it's the main thing standing between "report" and "report that holds confidence."

### P1.4 EDA report artifact (make EDA reviewable, not just chat-transient)
Right now EDA findings live only in the chat transcript and one Plan-row summary. For your "EDA report that holds confidence and improves explainability" requirement, `eda-workflow` should end by writing `.eds/eda/EDA.md` + saved figures:
- The question→answer→decision list (already produced — just persist it)
- Class-conditional overlay plots (violin/box) for the top-signal features — the visual a reviewer anchors on; medians in text don't do this
- A correlation heatmap of the feature set (residual structure among "independent" features affects linear-model coefficient stability — relevant since LR coefficients are your explainability story)
- A one-line "so the model should work because…" synthesis linking EDA signal to the modeling choice

`notebook-assembly` (P1.2) then embeds these figures rather than regenerating plots ad hoc.

### P1.5 Preprocessing as a Pipeline object, not loose cells
The fraud notebook computes engineered features with inline pandas in multiple cells. For pre-production, the FDE stage's *output* should include a fitted-or-fittable `sklearn.Pipeline`/`FunctionTransformer` chain (or a single `build_features(df) -> df` function written to `.eds/features.py`) that both the notebook and `inference.py` (P1.1) import. One definition, two consumers — this is the item that prevents train/serve skew when you modularize.

---

## P2 — Harden the workflow (process + guardrails)

### P2.1 A "stay on the paved road" rule for the driving agent
The recurring pattern in your transcript: when a plugin script didn't fit (wrong metric, broken calibration), the assistant improvised inline Python and moved on — losing the audit trail (`experiment_log.json` disagrees with the narrative). Add to `EDS.md` / `AGENTS.md`: *if a skill script can't express the Brief's requirement, the fix is to patch the script (or log an `eds:deferred` debt marker), never to silently route around it.* The hooks system (`harvest-debt.js` already exists) can collect these markers — use it.

### P2.2 Post-stage assertion gates
`scripts/gates/` exists but gates are mostly record-keeping. Add cheap numeric assertions per stage that fail loudly:
- post-calibration: AUPRC(before) − AUPRC(after) < ε (catches P0.2-class bugs automatically)
- post-split: no duplicate row straddles the train/test boundary (your own audit flagged this; nothing enforces it)
- post-FDE: selected features exist in both train and test with identical dtypes
- post-champion: `champion.json.metric_name` == contract metric

### P2.3 Fix `select_metric`'s universal ROC-AUC default (covered in P0.1) and audit the other probes for the same "reasonable default that's wrong for imbalanced data" pattern — `quick_relationships.py` (correlation vs a 0.17% target is noisy) and `funnel.py`'s stage-4 univariate ranking are the two to check.

---

## P3 — Nice-to-have (after the above)

- **SHAP/explanation stage** as an optional post-champion skill — LR coefficients sufficed here, but the moment a tree model wins champion, your explainability story needs it.
- **`eds:resume`** — regenerate a session's context from `.eds/` artifacts so a new session can pick up mid-lifecycle without replaying the transcript (the Brief's Plan table already carries most of this; formalize it).
- **Benchmark the fixes**: the repo already has `benchmarks/` with promptfoo config — add the fraud dataset as a fixture and encode P0.1/P0.2 as regression tests ("contract metric matches Brief," "calibration preserves AUPRC") so these bugs can't silently return.
- **Cost-matrix elicitation** in decision-optimization: the skill currently lets the agent assume a matrix with a comment; better to make it a structured `user-signoff` gate (like evaluation-contract) whenever no real costs exist — the threshold is the most business-consequential number in the whole pipeline.

---

## Suggested sequencing

**Week 1 (P0):** the three correctness fixes + regression tests for each. Small diffs, big trust gain.
**Week 2–3 (P1):** `model-handoff` and `bootstrap_ci.py` first (smallest, highest leverage), then `notebook-assembly`, then the EDA artifact + features-as-pipeline. After this, a full project run should end with: a model bundle you can load, a generated notebook that passed `maturity_check`, and a report whose headline metric carries a computed interval.
**Ongoing (P2):** gates and the paved-road rule as you touch each stage.

**Acceptance test for the whole plan:** rerun the exact same Kaggle fraud project end-to-end. Success = zero ad hoc inline scripts needed for metrics/calibration/thresholds, `experiment_log.json` says `average_precision` everywhere, `.eds/models/bundle/` loads and scores a raw dataframe, and the notebook was generated (not freehanded) and passes rung-2 hygiene.