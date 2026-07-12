#!/usr/bin/env python3
"""MDE — Calibration check (M3: calibrate before any threshold).

A model's predicted probabilities should reflect true frequencies.
Calibration is checked BEFORE any threshold is set — decision-optimization
depends on calibrated scores. An uncalibrated model with a threshold is
actively misleading.

Usage:
    python calibration.py check <path.csv> --y-true <col> --y-prob <col> \
        [--n-bins 10] [--out .eds/models/calibration_report.json]

    python calibration.py fix \
        --fit-path cal_predictions.csv \
        --apply-path test_predictions.csv \
        --y-true <col> --y-prob <col> \
        --method isotonic|platt \
        [--out calibrated_probs.csv]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd


def calibration_check(y_true, y_prob, n_bins=10):
    """Compute calibration curve and metrics."""
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = []
    observed_freqs = []
    predicted_means = []
    bin_counts = []

    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if i == n_bins - 1:
            mask = (y_prob >= bins[i]) & (y_prob <= bins[i + 1])
        n = mask.sum()
        if n == 0:
            continue
        bin_centers.append((bins[i] + bins[i + 1]) / 2)
        observed_freqs.append(y_true[mask].mean())
        predicted_means.append(y_prob[mask].mean())
        bin_counts.append(int(n))

    # Expected Calibration Error (ECE)
    total = sum(bin_counts)
    ece = sum(
        (count / total) * abs(obs - pred)
        for count, obs, pred in zip(bin_counts, observed_freqs, predicted_means)
    ) if total > 0 else 0.0

    # Brier score
    brier = float(np.mean((y_prob - y_true) ** 2))

    # Max calibration error (worst bin)
    max_ce = max(
        abs(obs - pred) for obs, pred in zip(observed_freqs, predicted_means)
    ) if observed_freqs else 0.0

    return {
        "ece": round(ece, 4),
        "max_calibration_error": round(max_ce, 4),
        "brier_score": round(brier, 6),
        "n_bins_used": len(bin_centers),
        "bins": [
            {"center": round(c, 3), "predicted": round(p, 4),
             "observed": round(o, 4), "count": n}
            for c, p, o, n in zip(bin_centers, predicted_means, observed_freqs, bin_counts)
        ],
        "verdict": _calibration_verdict(ece, max_ce),
    }


def _calibration_verdict(ece, max_ce):
    if ece < 0.02 and max_ce < 0.05:
        return "well-calibrated"
    if ece < 0.05 and max_ce < 0.10:
        return "acceptably calibrated — minor adjustments may help"
    if ece < 0.10:
        return "poorly calibrated — recalibration recommended before threshold setting"
    return "severely miscalibrated — recalibration REQUIRED before any threshold"


def apply_calibration(y_true_train, y_prob_train, y_prob_test, method="isotonic"):
    """Apply post-hoc calibration."""
    if method == "platt":
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.base import BaseEstimator, ClassifierMixin

        class ProbWrapper(BaseEstimator, ClassifierMixin):
            def fit(self, X, y): return self
            def predict_proba(self, X):
                return np.column_stack([1 - X.ravel(), X.ravel()])
            classes_ = np.array([0, 1])

        wrapper = ProbWrapper()
        cal = CalibratedClassifierCV(wrapper, method="sigmoid", cv="prefit")
        cal.fit(y_prob_train.reshape(-1, 1), y_true_train)
        return cal.predict_proba(y_prob_test.reshape(-1, 1))[:, 1]

    elif method == "isotonic":
        from sklearn.isotonic import IsotonicRegression
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(y_prob_train, y_true_train)
        return iso.predict(y_prob_test)

    raise ValueError(f"Unknown calibration method: {method}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    check_cmd = sub.add_parser("check")
    check_cmd.add_argument("path")
    check_cmd.add_argument("--y-true", required=True)
    check_cmd.add_argument("--y-prob", required=True)
    check_cmd.add_argument("--n-bins", type=int, default=10)
    check_cmd.add_argument("--out", default=".eds/models/calibration_report.json")

    fix_cmd = sub.add_parser("fix")
    fix_cmd.add_argument("--fit-path", required=True,
                         help="CSV with predictions on a held-out calibration split (from train side)")
    fix_cmd.add_argument("--apply-path", required=True,
                         help="CSV with predictions on the test set to calibrate")
    fix_cmd.add_argument("--y-true", required=True)
    fix_cmd.add_argument("--y-prob", required=True)
    fix_cmd.add_argument("--method", choices=["isotonic", "platt"], default="platt")
    fix_cmd.add_argument("--out", default="calibrated_probs.csv")

    args = ap.parse_args()

    if args.cmd == "check":
        df = pd.read_csv(args.path)
        y_true = df[args.y_true].values.astype(float)
        y_prob = df[args.y_prob].values.astype(float)
        report = calibration_check(y_true, y_prob, n_bins=args.n_bins)

        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Calibration: ECE={report['ece']:.4f}, "
              f"max_CE={report['max_calibration_error']:.4f}, "
              f"Brier={report['brier_score']:.6f}")
        print(f"Verdict: {report['verdict']}")
        print(f"Report: {args.out}")

    elif args.cmd == "fix":
        from sklearn.metrics import average_precision_score

        fit_df = pd.read_csv(args.fit_path)
        apply_df = pd.read_csv(args.apply_path)

        y_true_fit = fit_df[args.y_true].values.astype(float)
        y_prob_fit = fit_df[args.y_prob].values.astype(float)
        y_true_apply = apply_df[args.y_true].values.astype(float)
        y_prob_apply = apply_df[args.y_prob].values.astype(float)

        # Guardrail 1: refuse isotonic when fit set has < 200 positives
        n_positives = int(y_true_fit.sum())
        if args.method == "isotonic" and n_positives < 200:
            print(f"REFUSED: isotonic calibration requires density — fit set has only "
                  f"{n_positives} positives (< 200). Use --method platt instead.",
                  file=sys.stderr)
            sys.exit(1)

        # Compute pre-calibration AUPRC on apply set
        auprc_before = average_precision_score(y_true_apply, y_prob_apply)

        # Apply calibration
        calibrated = apply_calibration(
            y_true_fit, y_prob_fit, y_prob_apply, method=args.method,
        )

        # Guardrail 2: warn if rank-order changed (AUPRC drop)
        auprc_after = average_precision_score(y_true_apply, calibrated)
        rank_order_delta = auprc_after - auprc_before

        if rank_order_delta < -0.01:
            print(f"WARNING: AUPRC dropped after calibration "
                  f"({auprc_before:.4f} → {auprc_after:.4f}, Δ={rank_order_delta:.4f}). "
                  f"Monotone calibration should preserve rank-order — "
                  f"investigate whether the calibration fit set is representative.",
                  file=sys.stderr)

        out_df = apply_df.copy()
        out_df[f"{args.y_prob}_calibrated"] = calibrated
        out_df.to_csv(args.out, index=False)

        print(f"Calibrated ({args.method}) on {n_positives} positives from fit set")
        print(f"AUPRC: {auprc_before:.4f} → {auprc_after:.4f} (Δ={rank_order_delta:+.4f})")
        print(f"Output: {args.out} ({len(calibrated)} rows)")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
