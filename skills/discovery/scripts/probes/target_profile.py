#!/usr/bin/env python3
"""Probe: what does the target look like — balance, distribution, definition sanity?

Usage:
    python target_profile.py <path.csv> <target_col> [--sample-rows 200000]
"""
import argparse

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("target")
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    if args.target not in df.columns:
        print(f"## target_profile: FAILED — column '{args.target}' not found in {args.path}")
        return

    s = df[args.target]
    n = len(s)
    n_null = s.isna().sum()

    print(f"## target_profile: {args.path} [{args.target}]")
    print(f"- rows sampled: {n}")
    print(f"- nulls: {n_null} ({n_null / n:.2%})")

    s_notna = s.dropna()
    nunique = s_notna.nunique()
    print(f"- distinct values: {nunique}")

    if pd.api.types.is_numeric_dtype(s_notna) and nunique > 20:
        print("- looks continuous. summary stats:")
        print(f"  - mean={s_notna.mean():.4g}, std={s_notna.std():.4g}, "
              f"min={s_notna.min():.4g}, p50={s_notna.median():.4g}, max={s_notna.max():.4g}")
        skew = s_notna.skew()
        print(f"  - skew={skew:.2f}" + (" — heavily skewed, consider log/robust transform" if abs(skew) > 1 else ""))
    else:
        print("- looks categorical/binary. value counts:")
        vc = s_notna.value_counts()
        total = vc.sum()
        for val, count in vc.head(10).items():
            print(f"  - {val}: {count} ({count / total:.2%})")
        if nunique == 2:
            minority_rate = vc.min() / total
            print(f"- minority-class rate: {minority_rate:.2%}"
                  + (" — imbalanced, plan metric + resampling/weighting accordingly" if minority_rate < 0.1 else ""))
        if len(vc) > 10:
            print(f"  - ... {len(vc) - 10} more distinct values not shown")


if __name__ == "__main__":
    main()
