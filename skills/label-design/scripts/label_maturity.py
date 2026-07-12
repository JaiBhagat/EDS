#!/usr/bin/env python3
"""Probe: which rows haven't cleared the label's maturity window yet?

Usage:
    python label_maturity.py <path.csv> --event-date-col signup_date
        --observed-until 2026-06-01 --maturity-days 90 [--sample-rows 200000]

A row whose event happened fewer than --maturity-days before --observed-until
hasn't had time for the outcome to resolve — its label (however it's coded)
is censored, not a confirmed negative. Flags the count and rate so they can
be excluded rather than silently treated as label=0.
"""
import argparse

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--event-date-col", required=True)
    ap.add_argument("--observed-until", required=True)
    ap.add_argument("--maturity-days", type=int, required=True)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    print(f"## label_maturity: {args.path} [{args.event_date_col}, maturity={args.maturity_days}d]")
    if args.event_date_col not in df.columns:
        print(f"- FAILED — column '{args.event_date_col}' not found")
        return

    event_dates = pd.to_datetime(df[args.event_date_col], errors="coerce")
    observed_until = pd.to_datetime(args.observed_until)
    bad_dates = event_dates.isna().sum()

    age_days = (observed_until - event_dates).dt.days
    censored = age_days < args.maturity_days
    n_censored = int(censored.sum())
    n_valid = len(df) - bad_dates

    print(f"- rows: {len(df)}, unparseable dates: {bad_dates}")
    print(f"- censored (window not yet cleared): {n_censored} / {n_valid} ({n_censored / n_valid:.1%})" if n_valid else "- no valid dates to evaluate")
    if n_censored > 0:
        print(f"- these rows' labels are not yet final as of {args.observed_until} — exclude them from training/eval, don't code as negative.")
    else:
        print("- all rows have cleared the maturity window.")


if __name__ == "__main__":
    main()
