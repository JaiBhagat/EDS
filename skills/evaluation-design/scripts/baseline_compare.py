#!/usr/bin/env python3
"""Probe: is "the model beats baseline" a real win or resampling noise?

Usage:
    python baseline_compare.py <path.csv> --y-true y --y-baseline pred_base
        --y-model pred_model [--metric auto|auc|accuracy|mae|rmse]
        [--n-boot 2000] [--sample-rows 200000]

Bootstraps the per-row metric difference (model - baseline) and reports a
95% interval. If that interval contains zero, the improvement is not
distinguishable from noise at this sample size — say so, don't report the
higher point estimate as a win.
"""
import argparse

import numpy as np
import pandas as pd


def _metric(y_true, y_pred, metric):
    if metric == "auc":
        from sklearn.metrics import roc_auc_score
        return roc_auc_score(y_true, y_pred)
    if metric == "accuracy":
        return (y_true == np.round(y_pred)).mean()
    if metric == "mae":
        return -np.abs(y_true - y_pred).mean()  # negated so "higher is better" holds throughout
    if metric == "rmse":
        return -np.sqrt(np.mean((y_true - y_pred) ** 2))
    raise ValueError(metric)


def _infer_metric(y_true):
    return "auc" if pd.Series(y_true).nunique() == 2 else "rmse"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--y-true", required=True)
    ap.add_argument("--y-baseline", required=True)
    ap.add_argument("--y-model", required=True)
    ap.add_argument("--metric", default="auto", choices=["auto", "auc", "accuracy", "mae", "rmse"])
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    missing = [c for c in (args.y_true, args.y_baseline, args.y_model) if c not in df.columns]
    if missing:
        print(f"## baseline_compare: FAILED — column(s) not found: {missing}")
        return
    df = df.dropna(subset=[args.y_true, args.y_baseline, args.y_model])

    y = df[args.y_true].values
    base = df[args.y_baseline].values
    model = df[args.y_model].values
    metric = args.metric if args.metric != "auto" else _infer_metric(y)

    rng = np.random.default_rng(args.seed)
    n = len(df)
    diffs = np.empty(args.n_boot)
    for i in range(args.n_boot):
        idx = rng.integers(0, n, n)
        diffs[i] = _metric(y[idx], model[idx], metric) - _metric(y[idx], base[idx], metric)

    point_diff = _metric(y, model, metric) - _metric(y, base, metric)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    significant = lo > 0 or hi < 0

    print(f"## baseline_compare: {args.path} [metric={metric}, n={n}, n_boot={args.n_boot}]")
    print(f"- point estimate (model - baseline): {point_diff:+.4f}")
    print(f"- 95% bootstrap interval: [{lo:+.4f}, {hi:+.4f}]")
    if significant and point_diff > 0:
        print("- model beats baseline — improvement survives resampling noise.")
    elif significant and point_diff < 0:
        print("- baseline beats model — do not ship the model on this evidence.")
    else:
        print("- interval spans zero — no significant difference from baseline at this sample size.")


if __name__ == "__main__":
    main()
