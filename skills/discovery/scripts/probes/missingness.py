#!/usr/bin/env python3
"""Probe: where are the holes, and are they random or structural?

Usage:
    python missingness.py <path.csv> [--sample-rows 200000] [--corr-threshold 0.5]

Flags columns with high null rates, and pairs of columns whose nullness is
correlated (a sign of structural missingness — e.g. "discount_pct is null
exactly when promo_id is null" — rather than random noise).
"""
import argparse

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--sample-rows", type=int, default=200_000)
    ap.add_argument("--corr-threshold", type=float, default=0.5)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    n = len(df)
    null_rates = df.isna().mean().sort_values(ascending=False)

    print(f"## missingness: {args.path}")
    print(f"- rows sampled: {n}")
    print("- null rate by column (sorted, >0 only):")
    any_null = False
    for col, rate in null_rates.items():
        if rate > 0:
            any_null = True
            print(f"  - {col}: {rate:.2%}")
    if not any_null:
        print("  - none — no nulls in sampled rows.")
        return

    # Structural missingness: correlation between null-indicator columns.
    null_cols = [c for c in df.columns if null_rates[c] > 0]
    if len(null_cols) >= 2:
        null_mask = df[null_cols].isna().astype(int)
        corr = null_mask.corr()
        print(f"- structural missingness (null-indicator correlation > {args.corr_threshold}):")
        found = False
        for i, c1 in enumerate(null_cols):
            for c2 in null_cols[i + 1:]:
                r = corr.loc[c1, c2]
                if pd.notna(r) and abs(r) > args.corr_threshold:
                    found = True
                    print(f"  - {c1} <-> {c2}: r={r:.2f} — likely shared cause, not independent randomness.")
        if not found:
            print("  - none found — nulls look independent across columns (consistent with random, not structural).")


if __name__ == "__main__":
    main()
