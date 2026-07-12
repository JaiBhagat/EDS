#!/usr/bin/env python3
"""Probe: does the same entity appear in both sides of a split?

Usage:
    python split_overlap.py <split_a.csv> <split_b.csv> --key customer_id
        [--sample-rows 500000]

Any overlap is entity contamination across splits — never-cut item 2. Zero
tolerance: even a small overlap rate means the evaluation is partly measuring
memorization of specific entities, not generalization.
"""
import argparse

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split_a")
    ap.add_argument("split_b")
    ap.add_argument("--key", required=True)
    ap.add_argument("--sample-rows", type=int, default=500_000)
    args = ap.parse_args()

    a = pd.read_csv(args.split_a, nrows=args.sample_rows)
    b = pd.read_csv(args.split_b, nrows=args.sample_rows)

    if args.key not in a.columns or args.key not in b.columns:
        print(f"## split_overlap: FAILED — key '{args.key}' missing from one of the two files")
        return

    keys_a = set(a[args.key].dropna())
    keys_b = set(b[args.key].dropna())
    overlap = keys_a & keys_b

    print(f"## split_overlap: {args.split_a} <-> {args.split_b} [{args.key}]")
    print(f"- entities in A: {len(keys_a)}, entities in B: {len(keys_b)}")
    if overlap:
        preview = ", ".join(str(k) for k in list(overlap)[:5])
        more = f" (+{len(overlap) - 5} more)" if len(overlap) > 5 else ""
        print(f"- LEAK: {len(overlap)} overlapping entities ({len(overlap) / len(keys_a):.2%} of A) — {preview}{more}")
        print("- these entities must be assigned to only one split, never both.")
    else:
        print("- no overlap — splits are entity-disjoint on this key.")


if __name__ == "__main__":
    main()
