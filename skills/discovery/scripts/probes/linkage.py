#!/usr/bin/env python3
"""Probe: do the tables actually join, and at what cardinality?

Usage:
    python linkage.py <left.csv> <right.csv> --left-key col --right-key col
        [--sample-rows 200000]

Reports match rate and join cardinality (1:1, 1:many, many:1, many:many) —
the thing that silently inflates or drops rows when assumed wrong.
"""
import argparse

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--left-key", required=True)
    ap.add_argument("--right-key", required=True)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    left = pd.read_csv(args.left, nrows=args.sample_rows)
    right = pd.read_csv(args.right, nrows=args.sample_rows)

    print(f"## linkage: {args.left}[{args.left_key}] <-> {args.right}[{args.right_key}]")
    print(f"- left rows: {len(left)}, right rows: {len(right)}")

    left_keys = set(left[args.left_key].dropna())
    right_keys = set(right[args.right_key].dropna())
    matched = left_keys & right_keys
    left_only = left_keys - right_keys
    right_only = right_keys - left_keys

    print(f"- distinct left keys: {len(left_keys)}, distinct right keys: {len(right_keys)}")
    print(f"- matched keys: {len(matched)} "
          f"({len(matched) / len(left_keys):.2%} of left, {len(matched) / len(right_keys):.2%} of right)")
    if left_only:
        print(f"- left-only keys (would be dropped on inner join / become null on left join): {len(left_only)}")
    if right_only:
        print(f"- right-only keys (unmatched on the right side): {len(right_only)}")

    left_dupes = left[args.left_key].duplicated().sum()
    right_dupes = right[args.right_key].duplicated().sum()
    left_card = "many" if left_dupes else "one"
    right_card = "many" if right_dupes else "one"
    print(f"- cardinality: {left_card}:{right_card} "
          f"(left key repeats: {left_dupes}, right key repeats: {right_dupes})")
    if left_card == "many" and right_card == "many":
        print("- WARNING: many:many join — row count after join is NOT the sum of inputs, "
              "it can explode. Assert expected row count post-join before proceeding.")


if __name__ == "__main__":
    main()
