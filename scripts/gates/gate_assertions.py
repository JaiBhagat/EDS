#!/usr/bin/env python3
"""EDS gate: post-stage numeric assertions.

Cheap assertions that catch silently wrong results. Run after:
- post-calibration: AUPRC rank-order preserved
- post-split: no entity/row leaks across boundary
- post-FDE: selected features exist in both train and test with identical dtypes
- post-champion: champion metric_name == contract metric

Usage:
    python gate_assertions.py <assertion> [options]

    python gate_assertions.py calibration \
        --pre-path pre_cal_predictions.csv \
        --post-path post_cal_predictions.csv \
        --y-true label --y-prob-pre prob --y-prob-post prob_calibrated

    python gate_assertions.py split \
        --train-path train.csv --test-path test.csv \
        --entity-col user_id

    python gate_assertions.py features \
        --train-path train.csv --test-path test.csv \
        --feature-spec .eds/features/feature_spec.json

    python gate_assertions.py champion
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, find_eds_root, load_json


def assert_calibration(args):
    """Post-calibration: AUPRC(before) - AUPRC(after) < epsilon."""
    import numpy as np
    import pandas as pd
    from sklearn.metrics import average_precision_score

    root = find_eds_root(".")
    gate = GateResult("calibration-assertion")

    pre_df = pd.read_csv(args.pre_path)
    post_df = pd.read_csv(args.post_path)

    y_true = pre_df[args.y_true].values.astype(float)
    y_prob_pre = pre_df[args.y_prob_pre].values.astype(float)

    # Post may be a different file or same file with calibrated column
    if args.y_prob_post in post_df.columns:
        y_prob_post = post_df[args.y_prob_post].values.astype(float)
        y_true_post = post_df[args.y_true].values.astype(float)
    else:
        gate.check("post-column-exists", False,
                   f"Column '{args.y_prob_post}' not found in {args.post_path}")
        gate.write_and_exit(root)
        return

    auprc_before = average_precision_score(y_true, y_prob_pre)
    auprc_after = average_precision_score(y_true_post, y_prob_post)
    delta = auprc_before - auprc_after

    epsilon = 0.01  # 1% tolerance
    gate.check(
        "auprc-rank-order-preserved",
        delta < epsilon,
        f"AUPRC before={auprc_before:.4f}, after={auprc_after:.4f}, "
        f"drop={delta:.4f} (threshold={epsilon})"
    )

    # Also check that calibrated probs are in [0, 1]
    in_range = (y_prob_post >= 0).all() and (y_prob_post <= 1).all()
    gate.check("calibrated-probs-in-range", in_range,
               f"min={y_prob_post.min():.4f}, max={y_prob_post.max():.4f}")

    gate.add_evidence(args.pre_path)
    gate.add_evidence(args.post_path)
    gate.write_and_exit(root)


def assert_split(args):
    """Post-split: no duplicate entity straddles the train/test boundary."""
    import pandas as pd

    root = find_eds_root(".")
    gate = GateResult("split-assertion")

    train_df = pd.read_csv(args.train_path, usecols=[args.entity_col])
    test_df = pd.read_csv(args.test_path, usecols=[args.entity_col])

    train_entities = set(train_df[args.entity_col].dropna().unique())
    test_entities = set(test_df[args.entity_col].dropna().unique())

    overlap = train_entities & test_entities
    gate.check(
        "no-entity-leak-across-split",
        len(overlap) == 0,
        f"{len(overlap)} entities appear in both train and test"
        + (f" (first 5: {sorted(overlap)[:5]})" if overlap else "")
    )

    # Check for duplicate rows within each split
    train_dupes = train_df.duplicated().sum()
    test_dupes = test_df.duplicated().sum()
    gate.check(
        "no-duplicate-rows-in-test",
        test_dupes == 0,
        f"{test_dupes} duplicate rows in test set"
    )

    gate.add_evidence(args.train_path)
    gate.add_evidence(args.test_path)
    gate.write_and_exit(root)


def assert_features(args):
    """Post-FDE: selected features exist in both train and test with identical dtypes."""
    import pandas as pd

    root = find_eds_root(".")
    gate = GateResult("features-assertion")

    spec = load_json(Path(args.feature_spec))
    if spec is None:
        gate.check("feature-spec-exists", False, f"{args.feature_spec} not found")
        gate.write_and_exit(root)
        return

    feature_names = spec.get("feature_names", [])
    expected_dtypes = spec.get("dtypes", {})

    train_df = pd.read_csv(args.train_path, nrows=100)
    test_df = pd.read_csv(args.test_path, nrows=100)

    # Check all features exist in both
    train_missing = [f for f in feature_names if f not in train_df.columns]
    test_missing = [f for f in feature_names if f not in test_df.columns]

    gate.check(
        "features-in-train",
        len(train_missing) == 0,
        f"{len(train_missing)} features missing from train: {train_missing[:5]}"
        if train_missing else f"all {len(feature_names)} features present"
    )
    gate.check(
        "features-in-test",
        len(test_missing) == 0,
        f"{len(test_missing)} features missing from test: {test_missing[:5]}"
        if test_missing else f"all {len(feature_names)} features present"
    )

    # Check dtype consistency
    dtype_mismatches = []
    for feat in feature_names:
        if feat in train_df.columns and feat in test_df.columns:
            if train_df[feat].dtype != test_df[feat].dtype:
                dtype_mismatches.append(
                    f"{feat}: train={train_df[feat].dtype}, test={test_df[feat].dtype}"
                )

    gate.check(
        "dtype-consistency",
        len(dtype_mismatches) == 0,
        f"{len(dtype_mismatches)} dtype mismatches: {dtype_mismatches[:3]}"
        if dtype_mismatches else "all dtypes match"
    )

    gate.add_evidence(args.feature_spec)
    gate.write_and_exit(root)


def assert_champion(args):
    """Post-champion: champion metric_name == contract metric."""
    root = find_eds_root(".")
    gate = GateResult("champion-assertion")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ not found")
        gate.write_and_exit(Path("."))
        return

    models_dir = root / ".eds" / "models"
    champion = load_json(models_dir / "champion.json")
    contract = load_json(models_dir / "validation_contract.json")

    if champion is None:
        gate.check("champion-exists", False, "champion.json not found")
        gate.write_and_exit(root)
        return
    gate.check("champion-exists", True, "champion.json found")

    if contract is None:
        gate.check("contract-exists", False, "validation_contract.json not found")
        gate.write_and_exit(root)
        return
    gate.check("contract-exists", True, "validation_contract.json found")

    # The key assertion: metric names must match
    champion_metric = champion.get("metric_name", champion.get("metric", ""))
    contract_metric = contract.get("metric", "")

    gate.check(
        "metric-name-matches-contract",
        champion_metric == contract_metric,
        f"champion metric='{champion_metric}', contract metric='{contract_metric}'"
    )

    gate.add_evidence(str(models_dir / "champion.json"))
    gate.add_evidence(str(models_dir / "validation_contract.json"))
    gate.write_and_exit(root)


def main():
    ap = argparse.ArgumentParser(description="Post-stage numeric assertions")
    sub = ap.add_subparsers(dest="assertion")

    # Calibration assertion
    cal = sub.add_parser("calibration")
    cal.add_argument("--pre-path", required=True)
    cal.add_argument("--post-path", required=True)
    cal.add_argument("--y-true", required=True)
    cal.add_argument("--y-prob-pre", required=True)
    cal.add_argument("--y-prob-post", required=True)

    # Split assertion
    split = sub.add_parser("split")
    split.add_argument("--train-path", required=True)
    split.add_argument("--test-path", required=True)
    split.add_argument("--entity-col", required=True)

    # Features assertion
    feat = sub.add_parser("features")
    feat.add_argument("--train-path", required=True)
    feat.add_argument("--test-path", required=True)
    feat.add_argument("--feature-spec", default=".eds/features/feature_spec.json")

    # Champion assertion
    sub.add_parser("champion")

    args = ap.parse_args()

    if args.assertion == "calibration":
        assert_calibration(args)
    elif args.assertion == "split":
        assert_split(args)
    elif args.assertion == "features":
        assert_features(args)
    elif args.assertion == "champion":
        assert_champion(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
