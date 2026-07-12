#!/usr/bin/env python3
"""Probe: what windows exist, are there gaps, does history reach the horizon needed?

Usage:
    python time_coverage.py <path.csv> <date_col> [--freq D] [--unit auto]
        [--sample-rows 500000]

freq follows pandas offset aliases (D, W, M, ...). Detects missing periods in
the expected calendar between min and max, which is often more informative
than raw row counts.

--unit: s|ms|epoch|auto. When auto (default), detects if the column is numeric
elapsed time (e.g. seconds since experiment start) vs calendar datetime.
Numeric elapsed columns get a different analysis: span, monotonicity, per-bin
volume — not calendar gap detection which is meaningless for them.
"""
import argparse

import numpy as np
import pandas as pd


def is_elapsed_numeric(series: pd.Series) -> bool:
    """Detect if a numeric column is elapsed time (not a real datetime).

    Heuristic: if pd.to_datetime produces dates that all collapse near 1970,
    the column is likely seconds/ms elapsed, not a timestamp.
    """
    if not pd.api.types.is_numeric_dtype(series):
        return False
    sample = series.dropna().head(1000)
    if sample.empty:
        return False
    dt_parsed = pd.to_datetime(sample, errors="coerce", unit="s")
    if dt_parsed.isna().all():
        return True
    # If all parsed dates are within a day of epoch, it's elapsed
    years = dt_parsed.dropna().dt.year
    if years.empty:
        return True
    return years.max() < 1971 and years.min() >= 1969


def analyze_elapsed(series: pd.Series, unit: str, col_name: str):
    """Analyze a numeric elapsed-time column."""
    vals = series.dropna()
    span_raw = float(vals.max() - vals.min())

    # Convert to human-readable span
    if unit in ("ms", "milliseconds"):
        span_seconds = span_raw / 1000
    else:  # default to seconds
        span_seconds = span_raw

    if span_seconds < 3600:
        span_str = f"{span_seconds:.1f} seconds"
    elif span_seconds < 86400:
        span_str = f"{span_seconds / 3600:.2f} hours"
    else:
        span_str = f"{span_seconds / 86400:.2f} days ({span_seconds / 3600:.1f} hours)"

    print(f"## time_coverage: [{col_name}] — ELAPSED TIME (numeric)")
    print(f"- unit: {unit}")
    print(f"- span: {vals.min():.2f} → {vals.max():.2f} ({span_str})")
    print(f"- rows: {len(vals)}")

    # Monotonicity check
    diffs = vals.diff().dropna()
    n_negative = (diffs < 0).sum()
    if n_negative == 0:
        print("- monotonicity: strictly non-decreasing ✓")
    else:
        pct_neg = n_negative / len(diffs) * 100
        print(f"- monotonicity: {n_negative} reversals ({pct_neg:.1f}%) — "
              "NOT monotone, may represent interleaved events")

    # Per-bin volume (10 equal-width bins)
    n_bins = min(10, len(vals))
    bins = pd.cut(vals, bins=n_bins)
    bin_counts = bins.value_counts().sort_index()
    cv = bin_counts.std() / bin_counts.mean() if bin_counts.mean() > 0 else float("nan")
    print(f"- volume distribution across {n_bins} bins: CV={cv:.2f}"
          + (" — uneven volume across time" if cv > 0.5 else " — relatively uniform"))

    # Percentiles
    pcts = vals.quantile([0.01, 0.25, 0.5, 0.75, 0.99])
    print(f"- percentiles: p1={pcts.iloc[0]:.2f}, p25={pcts.iloc[1]:.2f}, "
          f"median={pcts.iloc[2]:.2f}, p75={pcts.iloc[3]:.2f}, p99={pcts.iloc[4]:.2f}")


def analyze_datetime(dt: pd.Series, freq: str, col_name: str, n_bad: int):
    """Analyze a proper datetime column."""
    print(f"## time_coverage: [{col_name}]")
    if n_bad > 0:
        print(f"- WARNING: {n_bad} values failed to parse as dates.")
    if dt.empty:
        print("- no parseable dates found.")
        return

    span_start, span_end = dt.min(), dt.max()
    print(f"- coverage: {span_start.date()} -> {span_end.date()} ({(span_end - span_start).days} days)")

    expected = pd.date_range(span_start.normalize(), span_end.normalize(), freq=freq)
    present = pd.Index(dt.dt.normalize().unique())
    missing = expected.difference(present)
    print(f"- expected periods @ freq={freq}: {len(expected)}, present: {len(present)}, missing: {len(missing)}")
    if len(missing) > 0:
        preview = ", ".join(str(d.date()) for d in missing[:5])
        more = f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""
        print(f"- gaps found — first few: {preview}{more}")
    else:
        print("- no gaps at this frequency — coverage is contiguous.")

    # Rows per period, to spot volume collapse
    period_freq = freq if freq in ("D", "W", "M") else "D"
    per_period = dt.dt.to_period(period_freq).value_counts().sort_index()
    if len(per_period) > 1:
        cv = per_period.std() / per_period.mean() if per_period.mean() else float("nan")
        print(f"- row-count-per-period coefficient of variation: {cv:.2f}"
              + (" — volume swings a lot across periods, check for partial/incomplete periods" if cv > 0.5 else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("date_col")
    ap.add_argument("--freq", default="D")
    ap.add_argument("--unit", default="auto",
                    choices=["auto", "s", "ms", "epoch"],
                    help="Time unit for numeric columns (auto-detected by default)")
    ap.add_argument("--sample-rows", type=int, default=500_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    if args.date_col not in df.columns:
        print(f"## time_coverage: FAILED — column '{args.date_col}' not found in {args.path}")
        return

    col = df[args.date_col]

    # Detect elapsed numeric vs real datetime
    force_elapsed = args.unit in ("s", "ms")
    if force_elapsed or (args.unit == "auto" and is_elapsed_numeric(col)):
        unit = args.unit if args.unit != "auto" else "s"
        analyze_elapsed(col, unit, args.date_col)
    else:
        dt = pd.to_datetime(col, errors="coerce")
        n_bad = dt.isna().sum() - col.isna().sum()
        dt = dt.dropna()
        analyze_datetime(dt, args.freq, args.date_col, n_bad)


if __name__ == "__main__":
    main()
