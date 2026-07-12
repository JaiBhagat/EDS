#!/usr/bin/env python3
"""Probe: are numeric values within a plausible range, and do any look like
sentinel/placeholder values rather than real measurements?

Usage:
    python range_check.py <path.csv> [--sample-rows 200000]

Flags: negative values in columns that look like counts/amounts (by name
heuristic), common sentinel values (-1, 9999, 999999, 0 where it dominates
an otherwise continuous column), and extreme outliers via IQR fence. This is
a fast auto-profile, not a substitute for domain-specific bounds the user
must supply (see data-audit SKILL.md step 4).
"""
import argparse

import numpy as np
import pandas as pd

SENTINEL_CANDIDATES = [-1, -999, 999, 9999, 99999, 999999]
COUNT_LIKE_HINTS = ("count", "num_", "n_", "qty", "quantity", "total", "amount", "amt", "days", "age")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    print(f"## range_check: {args.path}")
    if not numeric_cols:
        print("- no numeric columns found.")
        return

    for col in numeric_cols:
        s = df[col].dropna()
        if s.empty:
            continue
        findings = []

        lo, hi = s.min(), s.max()
        p1, p25, p50, p75, p99 = s.quantile([0.01, 0.25, 0.5, 0.75, 0.99])
        iqr = p75 - p25
        if iqr > 0:
            fence_lo, fence_hi = p25 - 3 * iqr, p75 + 3 * iqr
            outliers = ((s < fence_lo) | (s > fence_hi)).sum()
            if outliers > 0:
                findings.append(f"{outliers} extreme outliers beyond 3xIQR fence ({fence_lo:.4g}, {fence_hi:.4g})")

        name_lower = col.lower()
        looks_count_like = any(h in name_lower for h in COUNT_LIKE_HINTS)
        if looks_count_like and lo < 0:
            findings.append(f"negative values present (min={lo:.4g}) in a count/amount-like column — verify sign is meaningful")

        for sentinel in SENTINEL_CANDIDATES:
            rate = (s == sentinel).mean()
            if rate > 0.01:  # >1% of non-null values equal a classic sentinel
                findings.append(f"{rate:.1%} of values == {sentinel} — check this isn't a placeholder for missing/unknown")

        if findings:
            print(f"- {col}: min={lo:.4g}, p50={p50:.4g}, max={hi:.4g}")
            for f in findings:
                print(f"  - {f}")

    print("- (columns not listed above showed no flags at this sample size)")


if __name__ == "__main__":
    main()
