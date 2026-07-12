#!/usr/bin/env python3
"""Probe: what windows exist, are there gaps, does history reach the horizon needed?

Usage:
    python time_coverage.py <path.csv> <date_col> [--freq D] [--sample-rows 500000]

freq follows pandas offset aliases (D, W, M, ...). Detects missing periods in
the expected calendar between min and max, which is often more informative
than raw row counts.
"""
import argparse

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("date_col")
    ap.add_argument("--freq", default="D")
    ap.add_argument("--sample-rows", type=int, default=500_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    if args.date_col not in df.columns:
        print(f"## time_coverage: FAILED — column '{args.date_col}' not found in {args.path}")
        return

    dt = pd.to_datetime(df[args.date_col], errors="coerce")
    n_bad = dt.isna().sum() - df[args.date_col].isna().sum()
    dt = dt.dropna()

    print(f"## time_coverage: {args.path} [{args.date_col}]")
    if n_bad > 0:
        print(f"- WARNING: {n_bad} values failed to parse as dates.")
    if dt.empty:
        print("- no parseable dates found.")
        return

    span_start, span_end = dt.min(), dt.max()
    print(f"- coverage: {span_start.date()} -> {span_end.date()} ({(span_end - span_start).days} days)")

    expected = pd.date_range(span_start.normalize(), span_end.normalize(), freq=args.freq)
    present = pd.Index(dt.dt.normalize().unique())
    missing = expected.difference(present)
    print(f"- expected periods @ freq={args.freq}: {len(expected)}, present: {len(present)}, missing: {len(missing)}")
    if len(missing) > 0:
        preview = ", ".join(str(d.date()) for d in missing[:5])
        more = f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""
        print(f"- gaps found — first few: {preview}{more}")
    else:
        print("- no gaps at this frequency — coverage is contiguous.")

    # Rows per period, to spot volume collapse (a common silent-gap signature)
    per_period = dt.dt.to_period(args.freq if args.freq in ("D", "W", "M") else "D").value_counts().sort_index()
    if len(per_period) > 1:
        cv = per_period.std() / per_period.mean() if per_period.mean() else float("nan")
        print(f"- row-count-per-period coefficient of variation: {cv:.2f}"
              + (" — volume swings a lot across periods, check for partial/incomplete periods" if cv > 0.5 else ""))


if __name__ == "__main__":
    main()
