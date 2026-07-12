#!/usr/bin/env python3
"""Probe: Population Stability Index (PSI) per column between a reference
window and a current window.

Usage:
    python drift_check.py <reference.csv> <current.csv>
        [--cols col1,col2] [--bins 10] [--psi-threshold 0.25]
        [--sample-rows 200000]

Numeric columns: binned into --bins quantile buckets from the reference
distribution, then current is scored against those same bucket edges.
Categorical columns: category proportions compared directly.

PSI < 0.1 negligible, 0.1-0.25 moderate, > 0.25 significant — standard
industry cutoffs, not something this script invents.
"""
import argparse

import numpy as np
import pandas as pd


def psi_numeric(ref, cur, bins):
    edges = np.unique(np.quantile(ref.dropna(), np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return None  # not enough distinct values to bin meaningfully
    edges[0], edges[-1] = -np.inf, np.inf
    ref_counts = pd.cut(ref.dropna(), edges).value_counts(sort=False)
    cur_counts = pd.cut(cur.dropna(), edges).value_counts(sort=False)
    return _psi_from_counts(ref_counts, cur_counts)


def psi_categorical(ref, cur):
    cats = pd.Index(ref.dropna().unique()).union(cur.dropna().unique())
    ref_counts = ref.value_counts().reindex(cats, fill_value=0)
    cur_counts = cur.value_counts().reindex(cats, fill_value=0)
    return _psi_from_counts(ref_counts, cur_counts)


def _psi_from_counts(ref_counts, cur_counts, epsilon=1e-4):
    ref_pct = (ref_counts / ref_counts.sum()).clip(lower=epsilon)
    cur_pct = (cur_counts / cur_counts.sum()).clip(lower=epsilon)
    return float(((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("current")
    ap.add_argument("--cols", default="")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--psi-threshold", type=float, default=0.25)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    ref_df = pd.read_csv(args.reference, nrows=args.sample_rows)
    cur_df = pd.read_csv(args.current, nrows=args.sample_rows)

    cols = [c.strip() for c in args.cols.split(",") if c.strip()] or [
        c for c in ref_df.columns if c in cur_df.columns
    ]

    print(f"## drift_check: {args.reference} (ref, n={len(ref_df)}) vs {args.current} (current, n={len(cur_df)})")
    results = []
    for col in cols:
        if col not in ref_df.columns or col not in cur_df.columns:
            continue
        if pd.api.types.is_numeric_dtype(ref_df[col]):
            psi = psi_numeric(ref_df[col], cur_df[col], args.bins)
        else:
            psi = psi_categorical(ref_df[col], cur_df[col])
        if psi is not None:
            results.append((col, psi))

    results.sort(key=lambda r: -r[1])
    flagged = [r for r in results if r[1] > args.psi_threshold]
    for col, psi in results:
        flag = " [FLAGGED]" if psi > args.psi_threshold else ""
        print(f"- {col}: PSI={psi:.4g}{flag}")

    if flagged:
        print(f"- {len(flagged)}/{len(results)} column(s) above threshold ({args.psi_threshold}) — investigate before trusting current predictions on these.")
    else:
        print("- no column above threshold — input distribution looks stable.")


if __name__ == "__main__":
    main()
