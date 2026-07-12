#!/usr/bin/env python3
"""Probe: quick leakage smell test over a modeling table.

Usage:
    python feature_availability_scan.py <path.csv> --target <col>
        [--cutoff-col <date-col>] [--sample-rows 50000] [--leak-threshold 0.98]

Flags two independent signals, neither of which proves leakage on its own —
both are "go verify this" flags, not verdicts:
  (a) features near-perfectly separating the target (reuses the correlation
      check from discovery's quick_relationships.py — if that probe already
      ran this session, this just re-confirms on the leakage-check pass).
  (b) column names matching post-outcome-sounding patterns (resolved,
      final_*, chargeback, refund, outcome, result, ...).

This script cannot verify point-in-time availability by itself — it has no
notion of when each feature value was computed relative to --cutoff-col, only
that a cutoff column exists. That check stays manual (see SKILL.md check 1).
"""
import argparse
import re

import numpy as np
import pandas as pd

NAME_PATTERNS = re.compile(
    r"(resolved|resolution|final_|chargeback|refund|outcome|result|closed_|settlement|actual_)",
    re.IGNORECASE,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--target", required=True)
    ap.add_argument("--cutoff-col")
    ap.add_argument("--sample-rows", type=int, default=50_000)
    ap.add_argument("--leak-threshold", type=float, default=0.98)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    print(f"## feature_availability_scan: {args.path} [{args.target}]")
    if args.target not in df.columns:
        print(f"- FAILED — target column '{args.target}' not found")
        return

    df = df.dropna(subset=[args.target])
    y_raw = df[args.target]
    is_classification = not pd.api.types.is_numeric_dtype(y_raw) or y_raw.nunique() <= 20
    y = y_raw.astype("category").cat.codes.values if is_classification else y_raw.values

    feature_cols = [c for c in df.columns if c != args.target]
    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]

    suspects = []
    for col in numeric_cols:
        s = df[col].fillna(df[col].median())
        if s.nunique() <= 1:
            continue
        corr = np.corrcoef(s, y)[0, 1]
        if pd.notna(corr) and abs(corr) >= args.leak_threshold:
            suspects.append(f"{col}: |corr|={abs(corr):.3f} with target")

    name_flags = [c for c in feature_cols if NAME_PATTERNS.search(c)]

    if suspects:
        print("- LEAKAGE-SUSPECT (near-perfect separation):")
        for s in suspects:
            print(f"  - {s} — verify this isn't derived from/after the target")
    else:
        print("- no near-perfectly-separating numeric features found at this sample size")

    if name_flags:
        print("- LEAKAGE-SUSPECT (post-outcome-sounding name):")
        for c in name_flags:
            print(f"  - {c} — check when this value is actually populated")
    else:
        print("- no column names matched post-outcome patterns")

    if args.cutoff_col:
        if args.cutoff_col in df.columns:
            print(f"- cutoff column '{args.cutoff_col}' present — point-in-time availability per feature still needs manual trace (see SKILL.md check 1), this script can't infer it")
        else:
            print(f"- cutoff column '{args.cutoff_col}' not found in table")


if __name__ == "__main__":
    main()
