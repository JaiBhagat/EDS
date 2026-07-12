#!/usr/bin/env python3
"""Bootstrap confidence intervals for model metrics.

Stratified resampling ensures every bootstrap draw contains positives,
even for highly imbalanced datasets. Used in three places:
1. Baseline bar — is LR really above the heuristic?
2. Champion vs. bar — did features really add lift?
3. Final report — headline metric with computed interval.

Usage:
    python bootstrap_ci.py <path.csv> --y-true <col> --y-prob <col> \
        --metric average_precision [--n-boot 2000] [--ci 0.90] \
        [--out .eds/models/bootstrap_ci.json]

    # Compare two models:
    python bootstrap_ci.py <path.csv> --y-true <col> --y-prob <col> \
        --y-prob-baseline <col> --metric average_precision
"""
import argparse
import json
import os
import sys

import numpy as np


def stratified_bootstrap_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    metric_fn,
    n_boot: int = 2000,
    ci: float = 0.90,
    seed: int = 42,
) -> dict:
    """Compute bootstrap CI with stratified resampling.

    Stratification ensures every resample has positives and negatives,
    which is critical when the positive rate is low (e.g., fraud).
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)

    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]
    n_pos, n_neg = len(pos_idx), len(neg_idx)

    if n_pos == 0 or n_neg == 0:
        return {
            "point_estimate": float(metric_fn(y_true, y_score)),
            "ci_lower": None,
            "ci_upper": None,
            "ci_level": ci,
            "n_boot": 0,
            "warning": "Cannot bootstrap: need both positives and negatives",
        }

    scores = []
    for _ in range(n_boot):
        # Stratified resample: sample pos and neg indices separately
        boot_pos = rng.choice(pos_idx, size=n_pos, replace=True)
        boot_neg = rng.choice(neg_idx, size=n_neg, replace=True)
        boot_idx = np.concatenate([boot_pos, boot_neg])

        try:
            s = metric_fn(y_true[boot_idx], y_score[boot_idx])
            scores.append(s)
        except (ValueError, ZeroDivisionError):
            continue

    if len(scores) < n_boot * 0.5:
        return {
            "point_estimate": float(metric_fn(y_true, y_score)),
            "ci_lower": None,
            "ci_upper": None,
            "ci_level": ci,
            "n_boot": len(scores),
            "warning": f"Only {len(scores)}/{n_boot} bootstrap samples succeeded",
        }

    scores = np.array(scores)
    alpha = (1 - ci) / 2
    lower = float(np.percentile(scores, alpha * 100))
    upper = float(np.percentile(scores, (1 - alpha) * 100))
    point = float(metric_fn(y_true, y_score))

    return {
        "point_estimate": round(point, 6),
        "ci_lower": round(lower, 6),
        "ci_upper": round(upper, 6),
        "ci_level": ci,
        "ci_width": round(upper - lower, 6),
        "n_boot": len(scores),
        "n_positives": int(n_pos),
        "n_total": int(n),
    }


def paired_bootstrap_test(
    y_true: np.ndarray,
    y_score_a: np.ndarray,
    y_score_b: np.ndarray,
    metric_fn,
    n_boot: int = 2000,
    ci: float = 0.90,
    seed: int = 42,
) -> dict:
    """Paired bootstrap test: is model A better than model B?

    Returns the CI of the difference (A - B). If CI excludes zero,
    the difference is significant at the given level.
    """
    rng = np.random.default_rng(seed)

    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]
    n_pos, n_neg = len(pos_idx), len(neg_idx)

    diffs = []
    for _ in range(n_boot):
        boot_pos = rng.choice(pos_idx, size=n_pos, replace=True)
        boot_neg = rng.choice(neg_idx, size=n_neg, replace=True)
        boot_idx = np.concatenate([boot_pos, boot_neg])

        try:
            sa = metric_fn(y_true[boot_idx], y_score_a[boot_idx])
            sb = metric_fn(y_true[boot_idx], y_score_b[boot_idx])
            diffs.append(sa - sb)
        except (ValueError, ZeroDivisionError):
            continue

    if not diffs:
        return {"delta": None, "significant": None, "warning": "No valid bootstrap samples"}

    diffs = np.array(diffs)
    alpha = (1 - ci) / 2
    lower = float(np.percentile(diffs, alpha * 100))
    upper = float(np.percentile(diffs, (1 - alpha) * 100))

    point_a = float(metric_fn(y_true, y_score_a))
    point_b = float(metric_fn(y_true, y_score_b))

    significant = (lower > 0) or (upper < 0)

    return {
        "score_a": round(point_a, 6),
        "score_b": round(point_b, 6),
        "delta": round(point_a - point_b, 6),
        "ci_lower": round(lower, 6),
        "ci_upper": round(upper, 6),
        "ci_level": ci,
        "significant": significant,
        "n_boot": len(diffs),
        "interpretation": (
            f"A is {'better' if point_a > point_b else 'worse'} by "
            f"{abs(point_a - point_b):.4f} "
            f"({'significant' if significant else 'NOT significant'} at {ci:.0%})"
        ),
    }


def get_metric_fn(metric_name: str):
    """Get the scoring function for a metric name."""
    from sklearn.metrics import average_precision_score, f1_score, roc_auc_score

    registry = {
        "roc_auc": roc_auc_score,
        "average_precision": average_precision_score,
        "f1": lambda yt, yp: f1_score(yt, (yp > 0.5).astype(int)),
    }
    if metric_name not in registry:
        print(f"Unknown metric '{metric_name}'. Available: {list(registry.keys())}",
              file=sys.stderr)
        sys.exit(1)
    return registry[metric_name]


def main():
    ap = argparse.ArgumentParser(
        description="Bootstrap confidence intervals for model metrics"
    )
    ap.add_argument("path", help="CSV with predictions and true labels")
    ap.add_argument("--y-true", required=True)
    ap.add_argument("--y-prob", required=True, help="Model A predicted probabilities")
    ap.add_argument("--y-prob-baseline", default=None,
                    help="Model B (baseline) predicted probabilities for paired test")
    ap.add_argument("--metric", default="average_precision",
                    choices=["roc_auc", "average_precision", "f1"])
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--ci", type=float, default=0.90)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None,
                    help="Output JSON path (default: .eds/models/bootstrap_ci.json)")
    args = ap.parse_args()

    import pandas as pd
    df = pd.read_csv(args.path)
    y_true = df[args.y_true].values.astype(float)
    y_score = df[args.y_prob].values.astype(float)
    metric_fn = get_metric_fn(args.metric)

    result = stratified_bootstrap_ci(
        y_true, y_score, metric_fn,
        n_boot=args.n_boot, ci=args.ci, seed=args.seed,
    )
    result["metric"] = args.metric

    print(f"## Bootstrap CI ({args.metric})")
    print(f"- point estimate: {result['point_estimate']:.4f}")
    if result["ci_lower"] is not None:
        print(f"- {args.ci:.0%} CI: [{result['ci_lower']:.4f}, {result['ci_upper']:.4f}] "
              f"(width={result['ci_width']:.4f})")
        print(f"- n_positives={result['n_positives']}, n_total={result['n_total']}, "
              f"n_boot={result['n_boot']}")
    else:
        print(f"- WARNING: {result.get('warning')}")

    # Paired comparison if baseline provided
    if args.y_prob_baseline:
        y_baseline = df[args.y_prob_baseline].values.astype(float)
        paired = paired_bootstrap_test(
            y_true, y_score, y_baseline, metric_fn,
            n_boot=args.n_boot, ci=args.ci, seed=args.seed,
        )
        result["paired_comparison"] = paired
        print(f"\n## Paired comparison vs baseline")
        print(f"- {paired['interpretation']}")
        print(f"- Δ CI: [{paired['ci_lower']:.4f}, {paired['ci_upper']:.4f}]")

    # Write output
    out_path = args.out or ".eds/models/bootstrap_ci.json"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nReport: {out_path}")


if __name__ == "__main__":
    main()
