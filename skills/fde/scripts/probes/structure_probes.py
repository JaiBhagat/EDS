#!/usr/bin/env python3
"""EDS FDE — reusable precondition probes for hypothesis families.

One probe generalizes across several families' precondition checks rather
than one probe per family — sixteen near-duplicate probes would just be
the same three underlying questions repeated: does linkage exist, is
there enough density, does history cover enough time/cohort.

Usage: import and call directly, or run as a CLI against a CSV.
"""
import argparse
import sys

import pandas as pd


def linkage_density(df, link_col):
    """Fraction of rows where link_col is non-null. Precondition for
    graph/sequence families — a near-empty link column means the join
    doesn't actually connect anything."""
    return float(df[link_col].notna().mean())


def event_density(df, entity_col, event_time_col):
    """Median events per entity, plus a summary. Precondition for
    behavioral/frequency/velocity/aggregation families."""
    counts = df.groupby(entity_col)[event_time_col].count()
    return float(counts.median()), counts.describe().to_dict()


def time_window_coverage(df, time_col, required_days):
    """Does history span at least required_days? Precondition for
    trend/seasonality families."""
    span = (pd.to_datetime(df[time_col]).max() - pd.to_datetime(df[time_col]).min()).days
    return int(span), span >= required_days


def cohort_size(df, cohort_col, min_members=20):
    """Smallest cohort size. Precondition for peer-comparison — below
    min_members the percentile/z-score is noise."""
    sizes = df.groupby(cohort_col).size()
    return int(sizes.min()), bool(sizes.min() >= min_members)


def _demo():
    df = pd.DataFrame({
        "entity": ["a", "a", "a", "b", "b", "c"],
        "event_time": pd.date_range("2026-01-01", periods=6, freq="30D"),
        "link": ["dev1", "dev1", None, "dev2", "dev2", "dev2"],
        "cohort": ["x", "x", "x", "y", "y", "y"],
    })

    density = linkage_density(df, "link")
    assert abs(density - (5 / 6)) < 1e-9, density

    median, summary = event_density(df, "entity", "event_time")
    assert median == 2.0, median

    span, covers_100 = time_window_coverage(df, "event_time", required_days=100)
    assert span == 150, span
    assert covers_100 is True

    min_size, ok = cohort_size(df, "cohort", min_members=3)
    assert min_size == 3, min_size
    assert ok is True
    min_size2, ok2 = cohort_size(df, "cohort", min_members=4)
    assert ok2 is False

    print("structure_probes.py self-test OK")


def _cli():
    parser = argparse.ArgumentParser(description="EDS FDE structure probes")
    parser.add_argument("path", nargs="?", help="CSV to probe")
    parser.add_argument("--entity-col")
    parser.add_argument("--time-col")
    parser.add_argument("--link-col")
    parser.add_argument("--cohort-col")
    args = parser.parse_args()

    if not args.path:
        _demo()
        return

    df = pd.read_csv(args.path)
    if args.link_col:
        print(f"linkage_density({args.link_col}) = {linkage_density(df, args.link_col):.3f}")
    if args.entity_col and args.time_col:
        median, summary = event_density(df, args.entity_col, args.time_col)
        print(f"event_density median = {median}, summary = {summary}")
    if args.time_col:
        span, ok = time_window_coverage(df, args.time_col, required_days=180)
        print(f"time_window span = {span} days, covers 180d = {ok}")
    if args.cohort_col:
        min_size, ok = cohort_size(df, args.cohort_col)
        print(f"smallest cohort = {min_size}, ok(>=20) = {ok}")


if __name__ == "__main__":
    _cli()
