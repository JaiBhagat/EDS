#!/usr/bin/env python3
"""Probe: on a sample, which fields plausibly carry signal — and which look
like leakage?

Usage:
    python quick_relationships.py <path.csv> <target_col> [--sample-rows 50000]
        [--leak-threshold 0.98]

Numeric features: absolute correlation with target. Categorical features:
normalized mutual information. A feature above --leak-threshold is flagged
leakage-suspect, not celebrated as a great predictor — near-perfect
separation this early is almost always the target leaking into a feature.
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
from sklearn.preprocessing import LabelEncoder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("target")
    ap.add_argument("--sample-rows", type=int, default=50_000)
    ap.add_argument("--leak-threshold", type=float, default=0.98)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    if args.target not in df.columns:
        print(f"## quick_relationships: FAILED — column '{args.target}' not found in {args.path}")
        return

    df = df.dropna(subset=[args.target])
    y_raw = df[args.target]
    is_classification = not pd.api.types.is_numeric_dtype(y_raw) or y_raw.nunique() <= 20

    print(f"## quick_relationships: {args.path} [{args.target}]")
    print(f"- rows sampled: {len(df)}, task inferred: {'classification' if is_classification else 'regression'}")

    feature_cols = [c for c in df.columns if c != args.target]
    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]

    if is_classification:
        y = LabelEncoder().fit_transform(y_raw.astype(str))
    else:
        y = y_raw.values

    results = []

    if numeric_cols:
        X_num = df[numeric_cols].fillna(df[numeric_cols].median(numeric_only=True))
        for col in numeric_cols:
            if X_num[col].nunique() <= 1:
                continue
            corr = np.corrcoef(X_num[col], y)[0, 1] if not is_classification else _point_biserial(X_num[col], y)
            if pd.notna(corr):
                results.append((col, "numeric", abs(corr)))

    if categorical_cols:
        X_cat = df[categorical_cols].fillna("__missing__").astype(str).apply(LabelEncoder().fit_transform)
        mi_fn = mutual_info_classif if is_classification else mutual_info_regression
        try:
            mi = mi_fn(X_cat, y, discrete_features=True, random_state=0)
            for col, score in zip(categorical_cols, mi):
                results.append((col, "categorical", score))
        except ValueError:
            pass

    results.sort(key=lambda r: r[2], reverse=True)
    print("- top signal (sorted by strength; numeric=|corr|, categorical=MI, not directly comparable):")
    for col, kind, score in results[:15]:
        flag = ""
        if kind == "numeric" and score >= args.leak_threshold:
            flag = "  <-- LEAKAGE-SUSPECT: near-perfect correlation, verify this isn't derived from/after the target"
        print(f"  - {col} ({kind}): {score:.3f}{flag}")

    if not results:
        print("  - no usable feature columns found.")


def _point_biserial(x, y_binary):
    """Correlation between a numeric feature and a binary/encoded target."""
    return np.corrcoef(x, y_binary)[0, 1]


if __name__ == "__main__":
    main()
