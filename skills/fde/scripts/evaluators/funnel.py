#!/usr/bin/env python3
"""EDS FDE — staged evaluation funnel (stages 0-10).

Cheapest-first, never-cut-first. Stages 0/1/2/3/5/7/9 hard-kill; stages
4/6 rank without evicting (interaction hypotheses legitimately fail
univariate screens — F1 exists so that isn't a license to skip having a
hypothesis, but it does mean stage 4 can't be the one that kills them).
Stage 8 needs human sign-off and stage 10 needs a real train/holdout
split, so neither runs automatically inside run_hard_kill_stages() below
-- call them explicitly once the earlier stages have done their job.

See skills/fde/references/evaluators/stage-*.md for the full metadata
(cost class, applicable task types) behind each stage.
"""
import json
import os
import re

import numpy as np
import pandas as pd

NAME_PATTERNS = re.compile(
    r"resolved|resolution|final_|chargeback|refund|outcome|result|closed_|settlement|actual_",
    re.I,
)


def _is_categorical_like(s: pd.Series) -> bool:
    """True for object, string, or categorical dtypes — the columns that
    need factorization.  Works across pandas 1.x–3.x."""
    return (
        pd.api.types.is_object_dtype(s)
        or pd.api.types.is_string_dtype(s)
        or isinstance(s.dtype, pd.CategoricalDtype)
    )


def _encode(df):
    """Factorize non-numeric columns, leave numeric alone, fill NaN with -1 —
    a cheap reference-model encoding, not the production encoding."""
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        if _is_categorical_like(df[col]):
            out[col] = pd.factorize(df[col])[0]
        else:
            out[col] = df[col]
    return out.fillna(-1)


def stage_0_leakage_scan(df, target, candidates, corr_cutoff=0.98):
    survivors, evictions = [], []
    y = df[target]
    for col in candidates:
        if NAME_PATTERNS.search(col):
            evictions.append((col, "name matches post-outcome vocabulary"))
            continue
        if pd.api.types.is_numeric_dtype(df[col]) and pd.api.types.is_numeric_dtype(y):
            corr = df[col].corr(y)
            if pd.notna(corr) and abs(corr) >= corr_cutoff:
                evictions.append((col, f"correlation with target {corr:.3f} >= cutoff {corr_cutoff} — suspiciously perfect"))
                continue
        survivors.append(col)
    return survivors, evictions


def stage_1_degenerate_filter(df, candidates, near_constant_frac=0.99):
    survivors, evictions = [], []
    seen_hashes = {}
    for col in candidates:
        s = df[col]
        top_frac = s.value_counts(normalize=True, dropna=False).iloc[0] if len(s) else 1.0
        if top_frac >= near_constant_frac:
            evictions.append((col, f"near-constant — {top_frac:.1%} single value"))
            continue
        h = int(pd.util.hash_pandas_object(s.fillna("__NA__")).sum())
        dup_of = next((other for other, other_h in seen_hashes.items() if other_h == h), None)
        if dup_of:
            evictions.append((col, f"duplicate of {dup_of} (identical values)"))
            continue
        seen_hashes[col] = h
        survivors.append(col)
    return survivors, evictions


def stage_2_missingness(df, candidates, max_missing_frac=0.8):
    survivors, evictions = [], []
    for col in candidates:
        frac = df[col].isna().mean()
        if frac >= max_missing_frac:
            evictions.append((col, f"missing {frac:.1%} of rows — can't drive the decision for most of the population"))
            continue
        survivors.append(col)
    return survivors, evictions


def stage_3_cardinality(df, candidates, max_categories=100):
    survivors, evictions = [], []
    for col in candidates:
        if _is_categorical_like(df[col]):
            nunique = df[col].nunique(dropna=True)
            if nunique > max_categories:
                evictions.append((col, f"{nunique} categories — explosive cardinality, cost/overfit hazard"))
                continue
        survivors.append(col)
    return survivors, evictions


def stage_4_univariate_signal(df, target, candidates):
    """Ranks, never hard-kills. Categorical columns get a spread-of-group-means
    proxy in place of a real MI/IV computation — cheap and directionally right
    for a screening stage, not a substitute for stage 6."""
    y = df[target]
    scores = {}
    for col in candidates:
        if pd.api.types.is_numeric_dtype(df[col]) and pd.api.types.is_numeric_dtype(y):
            corr = df[col].corr(y)
            scores[col] = float(abs(corr)) if pd.notna(corr) else 0.0
        else:
            grp = df.groupby(col)[target].mean()
            scores[col] = float(grp.std()) if len(grp) > 1 and pd.notna(grp.std()) else 0.0
    return scores


def stage_5_redundancy(df, candidates, corr_cluster_cutoff=0.9):
    survivors, evictions = [], []
    numeric = [c for c in candidates if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric = [c for c in candidates if c not in numeric]
    kept = []
    for col in numeric:
        redundant_with, redundant_corr = None, None
        for k in kept:
            corr = df[col].corr(df[k])
            if pd.notna(corr) and abs(corr) >= corr_cluster_cutoff:
                redundant_with, redundant_corr = k, corr
                break
        if redundant_with:
            evictions.append((col, f"correlation {redundant_corr:.3f} with kept feature {redundant_with} — redundant"))
        else:
            kept.append(col)
            survivors.append(col)
    survivors.extend(non_numeric)
    return survivors, evictions


def stage_6_model_importance(df, target, candidates, task="classification", n_folds=5, seed=7):
    """Fast reference-model importance on rotating folds (F7 — never the
    confirmation holdout)."""
    from sklearn.model_selection import KFold
    if task == "classification":
        from sklearn.ensemble import GradientBoostingClassifier as GBM
    else:
        from sklearn.ensemble import GradientBoostingRegressor as GBM

    X = _encode(df[candidates])
    y = df[target]
    kf = KFold(n_splits=n_folds, shuffle=False)  # rotating, never shuffled on time-relevant data
    importances = np.zeros(len(candidates))
    folds_run = 0
    for train_idx, _ in kf.split(X):
        model = GBM(n_estimators=50, max_depth=3, random_state=seed)
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        importances += model.feature_importances_
        folds_run += 1
    importances /= max(folds_run, 1)
    return dict(zip(candidates, importances.tolist()))


def stage_7_stability(df, target, candidates, time_col, n_slices=3, max_score_drift=0.4):
    """Compares raw univariate-signal scores (not percentile ranks) across
    time slices — with only a handful of slices, rank position swings by a
    fixed amount regardless of actual magnitude change, so magnitude is the
    signal that actually catches a feature whose importance decays."""
    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    slices = np.array_split(df_sorted, n_slices)
    per_slice_scores = [stage_4_univariate_signal(sl, target, candidates) for sl in slices if len(sl) >= 5]
    if len(per_slice_scores) < 2:
        return list(candidates), []  # not enough slices to judge — pass through, don't guess

    survivors, evictions = [], []
    for col in candidates:
        scores = [s[col] for s in per_slice_scores]
        drift = float(max(scores) - min(scores))
        if drift >= max_score_drift:
            evictions.append((col, f"signal drifts {drift:.2f} across {len(per_slice_scores)} time slices — unstable, production incident on a delay"))
        else:
            survivors.append(col)
    return survivors, evictions


def stage_8_business_explainability(candidates, confirmed):
    """confirmed: set/list of names a domain owner has signed off on. Not
    automatable — separates confirmed from unconfirmed, doesn't guess."""
    confirmed = set(confirmed)
    survivors = [c for c in candidates if c in confirmed]
    evictions = [(c, "no domain-owner sign-off yet") for c in candidates if c not in confirmed]
    return survivors, evictions


def stage_9_serving_review(catalog_entries, max_cost=None, require_online_available=True):
    """catalog_entries: [{name, cost, online_available}, ...] for surviving candidates."""
    survivors, evictions = [], []
    for entry in catalog_entries:
        if require_online_available and not entry.get("online_available", True):
            evictions.append((entry["name"], "not computable online — training/serving parity broken"))
            continue
        if max_cost is not None and entry.get("cost", 0) > max_cost:
            evictions.append((entry["name"], f"inference cost {entry.get('cost')} exceeds budget {max_cost}"))
            continue
        survivors.append(entry["name"])
    return survivors, evictions


def stage_10_confirmation(df_train, df_holdout, target, candidates, task="classification", touch_log_path=None, seed=7):
    """Touches the confirmation holdout EXACTLY once per campaign (F7).
    Refuses a second call if touch_log_path already records a touch."""
    if touch_log_path and os.path.exists(touch_log_path):
        with open(touch_log_path) as f:
            log = json.load(f)
        if log.get("touched"):
            raise RuntimeError(
                f"confirmation holdout already touched this campaign (see {touch_log_path}) — "
                "re-use requires an explicit '# eds: deferred — holdout re-use' marker, not a silent second look"
            )

    Xtr, Xho = _encode(df_train[candidates]), _encode(df_holdout[candidates])
    ytr, yho = df_train[target], df_holdout[target]

    if task == "classification":
        from sklearn.ensemble import GradientBoostingClassifier as GBM
        from sklearn.metrics import roc_auc_score
        model = GBM(n_estimators=50, max_depth=3, random_state=seed)
        model.fit(Xtr, ytr)
        score = float(roc_auc_score(yho, model.predict_proba(Xho)[:, 1]))
    else:
        from sklearn.ensemble import GradientBoostingRegressor as GBM
        from sklearn.metrics import mean_squared_error
        model = GBM(n_estimators=50, max_depth=3, random_state=seed)
        model.fit(Xtr, ytr)
        score = -float(np.sqrt(mean_squared_error(yho, model.predict(Xho))))

    if touch_log_path:
        os.makedirs(os.path.dirname(touch_log_path) or ".", exist_ok=True)
        with open(touch_log_path, "w") as f:
            json.dump({"touched": True, "score": score}, f)
    return score


def run_hard_kill_stages(df, target, candidates):
    """Chains stages 0-5 (the automatable hard-kill stages) — stages 6/7
    need a task type + time column so they're called separately, and
    8/9/10 need human/external inputs that can't be auto-chained."""
    trail = {"input": list(candidates)}
    survivors, evictions = stage_0_leakage_scan(df, target, candidates)
    trail["stage_0"] = {"survivors": survivors, "evictions": evictions}
    survivors, ev = stage_1_degenerate_filter(df, survivors)
    trail["stage_1"] = {"survivors": survivors, "evictions": ev}
    survivors, ev = stage_2_missingness(df, survivors)
    trail["stage_2"] = {"survivors": survivors, "evictions": ev}
    survivors, ev = stage_3_cardinality(df, survivors)
    trail["stage_3"] = {"survivors": survivors, "evictions": ev}
    trail["stage_4_scores"] = stage_4_univariate_signal(df, target, survivors)
    survivors, ev = stage_5_redundancy(df, survivors)
    trail["stage_5"] = {"survivors": survivors, "evictions": ev}
    return survivors, trail


def _demo():
    rng = np.random.default_rng(7)
    n = 400
    df = pd.DataFrame({
        "signal_good": rng.normal(size=n),
        "leak_perfect": None,  # filled below
        "near_constant": np.where(rng.random(n) < 0.995, 0, 1),
        "high_card_str": [f"id_{i}" for i in range(n)],
        "mostly_missing": [np.nan] * (n - 5) + list(rng.normal(size=5)),
        "event_time": pd.date_range("2024-01-01", periods=n, freq="D"),
    })
    y = (df["signal_good"] + rng.normal(scale=0.5, size=n) > 0).astype(int)
    df["target"] = y
    df["leak_perfect"] = y  # exact copy of target
    df["dup_of_signal_good"] = df["signal_good"]  # exact duplicate

    candidates = ["signal_good", "leak_perfect", "near_constant", "high_card_str", "mostly_missing", "dup_of_signal_good"]
    survivors, trail = run_hard_kill_stages(df, "target", candidates)

    assert "leak_perfect" not in survivors, "stage 0 should have caught the perfect-correlation leak"
    assert "near_constant" not in survivors, "stage 1 should have caught the near-constant column"
    assert "high_card_str" not in survivors, "stage 3 should have caught the high-cardinality string"
    assert "mostly_missing" not in survivors, "stage 2 should have caught the mostly-missing column"
    assert "signal_good" in survivors
    assert not ("dup_of_signal_good" in survivors and "signal_good" in survivors), "stage 5 should have kept only one of the redundant pair"

    # stage 7 stability: a feature that carries real signal early, then decays
    # into pure noise later — real signal instability, not just a sign flip
    # (stage 4 scores by abs(corr), so a sign flip alone wouldn't move the score).
    noise = rng.normal(size=n)
    df["unstable"] = np.where(df["event_time"] < df["event_time"].median(), df["signal_good"], noise)
    surv7, ev7 = stage_7_stability(df, "target", ["signal_good", "unstable"], time_col="event_time", n_slices=3)
    assert "unstable" not in surv7, f"stage 7 should flag the flip-signed feature as unstable, got survivors={surv7}"
    assert "signal_good" in surv7

    # stage 10: confirmation touch-once guard.
    split = n // 2
    df_train, df_holdout = df.iloc[:split], df.iloc[split:]
    touch_log = "/tmp/eds_fde_selftest_touch.json"
    if os.path.exists(touch_log):
        os.remove(touch_log)
    score = stage_10_confirmation(df_train, df_holdout, "target", ["signal_good"], touch_log_path=touch_log)
    assert 0.0 <= score <= 1.0
    try:
        stage_10_confirmation(df_train, df_holdout, "target", ["signal_good"], touch_log_path=touch_log)
        raise AssertionError("second confirmation touch should have raised")
    except RuntimeError:
        pass
    os.remove(touch_log)

    print("funnel.py self-test OK — survivors after stages 0-5:", survivors)


if __name__ == "__main__":
    _demo()
