#!/usr/bin/env python3
"""Probe: what threshold maximizes expected value, and what's the highest
threshold that respects a review-capacity constraint?

Usage:
    python threshold_ev.py <path.csv> --score-col score --y-true label
        --cost-matrix tp=10,fp=-2,fn=-8,tn=0 [--capacity 500]
        [--n-thresholds 100] [--sample-rows 200000]

Sweeps thresholds over the score, computes expected value per threshold
from the confusion-matrix counts, and reports the EV-optimal one. If
--capacity is given, also reports the highest threshold whose flagged
(predicted-positive) count stays at or under that capacity — the two may
disagree, and that disagreement is itself the finding worth reporting.
"""
import argparse

import numpy as np
import pandas as pd


def parse_cost_matrix(s):
    parts = dict(p.split("=") for p in s.split(","))
    return {k: float(v) for k, v in parts.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--score-col", required=True)
    ap.add_argument("--y-true", required=True)
    ap.add_argument("--cost-matrix", required=True, help="tp=<v>,fp=<v>,fn=<v>,tn=<v>")
    ap.add_argument("--capacity", type=int)
    ap.add_argument("--n-thresholds", type=int, default=100)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    print(f"## threshold_ev: {args.path} [{args.score_col} vs {args.y_true}]")
    missing = [c for c in (args.score_col, args.y_true) if c not in df.columns]
    if missing:
        print(f"- FAILED — column(s) not found: {missing}")
        return

    df = df.dropna(subset=[args.score_col, args.y_true])
    y = df[args.y_true].values
    score = df[args.score_col].values
    cost = parse_cost_matrix(args.cost_matrix)
    for k in ("tp", "fp", "fn", "tn"):
        cost.setdefault(k, 0.0)

    thresholds = np.linspace(score.min(), score.max(), args.n_thresholds)
    best_ev, best_t = -np.inf, thresholds[0]
    rows = []
    for t in thresholds:
        pred_pos = score >= t
        tp = int(((pred_pos) & (y == 1)).sum())
        fp = int(((pred_pos) & (y == 0)).sum())
        fn = int(((~pred_pos) & (y == 1)).sum())
        tn = int(((~pred_pos) & (y == 0)).sum())
        ev = tp * cost["tp"] + fp * cost["fp"] + fn * cost["fn"] + tn * cost["tn"]
        n_flagged = tp + fp
        rows.append((t, ev, n_flagged))
        if ev > best_ev:
            best_ev, best_t = ev, t

    cap_t = None
    if args.capacity is not None:
        feasible = [t for t, _, n in rows if n <= args.capacity]
        cap_t = max(feasible) if feasible else None

    print(f"- EV-optimal threshold: {best_t:.4g} (expected value: {best_ev:.4g})")
    if args.capacity is not None:
        if cap_t is not None:
            n_at_cap = next(n for t, _, n in rows if t == cap_t)
            print(f"- capacity-constrained threshold: {cap_t:.4g} (flags {n_at_cap}/{args.capacity})")
        else:
            print(f"- no threshold in the swept range keeps flagged volume within capacity={args.capacity}")
        if cap_t is not None and not np.isclose(cap_t, best_t):
            print(f"- EV-optimal and capacity-constrained thresholds disagree ({best_t:.4g} vs {cap_t:.4g}) — report both, don't silently pick one.")


if __name__ == "__main__":
    main()
