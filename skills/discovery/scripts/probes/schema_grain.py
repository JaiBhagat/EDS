#!/usr/bin/env python3
"""Probe: what is each table's grain, and does the data honor it?

Usage:
    python schema_grain.py <path.csv> [--grain col1,col2] [--sample-rows 200000]

Prints a compact structured block for the Problem Brief. Reads a sample by
default (nrows) so this stays a probe, not a full-dataset job.
"""
import argparse
import sys

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--grain", default=None, help="comma-separated candidate grain columns")
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    n = len(df)

    print(f"## schema_grain: {args.path}")
    print(f"- rows sampled: {n}")
    print(f"- columns: {len(df.columns)}")
    print("- dtypes:")
    for col, dt in df.dtypes.items():
        print(f"  - {col}: {dt}")

    if args.grain:
        grain_cols = [c.strip() for c in args.grain.split(",")]
        missing = [c for c in grain_cols if c not in df.columns]
        if missing:
            print(f"- grain check: FAILED — columns not found: {missing}")
            sys.exit(1)
        dupe_count = df.duplicated(subset=grain_cols).sum()
        uniq_count = df.drop_duplicates(subset=grain_cols).shape[0]
        print(f"- candidate grain: {grain_cols}")
        print(f"- unique combinations: {uniq_count} / {n} rows")
        if dupe_count:
            print(f"- grain check: FAILED — {dupe_count} duplicate rows on candidate grain "
                  f"({dupe_count / n:.2%}) — this grain does not hold, or dedup is needed first.")
        else:
            print("- grain check: PASSED — candidate grain is unique across sampled rows.")
    else:
        # Suggest candidate grain: columns whose nunique == n
        candidates = [c for c in df.columns if df[c].nunique(dropna=False) == n]
        print(f"- no --grain given. columns unique across sample (candidate keys): {candidates or 'none found'}")


if __name__ == "__main__":
    main()
