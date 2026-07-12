#!/usr/bin/env python3
"""Probe: per-slice error rate, flagging slices significantly worse than
overall (not just numerically worse — small slices are noisy by chance).

Usage:
    python slice_errors.py <path.csv> --y-true label --y-pred pred
        [--slice-cols region,channel] [--metric auto|error_rate|mae]
        [--min-slice-n 30] [--sample-rows 200000]

Classification (<=20 distinct y-true values): metric is mismatch rate,
significance via two-proportion z-test (slice vs. rest).
Regression: metric is MAE, significance via Welch's t-test on absolute
errors (slice vs. rest).
"""
import argparse

import numpy as np
import pandas as pd
from scipy.stats import norm, ttest_ind


def two_proportion_z(p1, n1, p2, n2):
    if n1 == 0 or n2 == 0:
        return None
    pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = (pooled * (1 - pooled) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return None
    z = (p1 - p2) / se
    return 2 * (1 - norm.cdf(abs(z)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--y-true", required=True)
    ap.add_argument("--y-pred", required=True)
    ap.add_argument("--slice-cols", default="")
    ap.add_argument("--metric", choices=["auto", "error_rate", "mae"], default="auto")
    ap.add_argument("--min-slice-n", type=int, default=30)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    print(f"## slice_errors: {args.path} [{args.y_true} vs {args.y_pred}]")
    for col in (args.y_true, args.y_pred):
        if col not in df.columns:
            print(f"- FAILED — column '{col}' not found")
            return

    y_true, y_pred = df[args.y_true], df[args.y_pred]
    is_classification = args.metric == "error_rate" or (
        args.metric == "auto" and y_true.nunique() <= 20
    )

    slice_cols = [c.strip() for c in args.slice_cols.split(",") if c.strip()]
    slice_cols = [c for c in slice_cols if c in df.columns]

    if is_classification:
        df["_error"] = (y_true.astype(str) != y_pred.astype(str)).astype(int)
        overall_rate = df["_error"].mean()
        print(f"- overall error rate: {overall_rate:.4g} (n={len(df)})")
    else:
        df["_error"] = (y_true - y_pred).abs()
        overall_rate = df["_error"].mean()
        print(f"- overall MAE: {overall_rate:.4g} (n={len(df)})")

    if not slice_cols:
        print("- no valid --slice-cols given, skipping per-slice breakdown")
        return

    flags = []
    for col in slice_cols:
        for value, group in df.groupby(col):
            n = len(group)
            if n < args.min_slice_n:
                continue
            if is_classification:
                p_slice = group["_error"].mean()
                rest = df[df[col] != value]
                p_rest = rest["_error"].mean()
                pval = two_proportion_z(p_slice, n, p_rest, len(rest))
                worse = p_slice > p_rest
            else:
                errs_slice = group["_error"]
                errs_rest = df[df[col] != value]["_error"]
                p_slice, p_rest = errs_slice.mean(), errs_rest.mean()
                pval = ttest_ind(errs_slice, errs_rest, equal_var=False).pvalue if len(errs_rest) > 1 else None
                worse = p_slice > p_rest
            if worse and pval is not None and pval < 0.05:
                flags.append((col, value, n, p_slice, pval))

    if not flags:
        print("- no slice significantly worse than the rest at alpha=0.05 (small slices need --min-slice-n lowered to check further, at the cost of more noise)")
        return

    flags.sort(key=lambda f: f[4])
    print("- flagged slices (significantly worse than rest):")
    for col, value, n, rate, pval in flags[:10]:
        print(f"  - {col}={value!r} (n={n}): {rate:.4g} vs overall {overall_rate:.4g}, p={pval:.3g}")


if __name__ == "__main__":
    main()
