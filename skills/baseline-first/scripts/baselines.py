#!/usr/bin/env python3
"""Probe: fit and score the standard baseline set, so a custom model has a
real bar to beat.

Usage:
    python baselines.py <path.csv> --target label
        [--split-date-col signup_date] [--split-frac 0.2]
        [--sample-rows 200000]

Classification (<=20 distinct target values): majority-class, logistic
regression, default-hyperparameter GBM, scored by AUC.
Regression: mean-predictor, last-value (if a date column is given, ordered
by it), default-hyperparameter GBM, scored by RMSE (reported as -RMSE so
"higher is better" holds, matching evaluation-design's convention).

If --split-date-col is given, the split is the oldest --split-frac rows for
training / newest for eval (time-respecting). Otherwise a random split is
used and flagged as such — never assume time doesn't matter, ask if unsure.
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import LabelEncoder


def time_split(df, date_col, split_frac):
    df = df.sort_values(date_col)
    cut = int(len(df) * (1 - split_frac))
    return df.iloc[:cut], df.iloc[cut:]


def random_split(df, split_frac, seed=0):
    df = df.sample(frac=1, random_state=seed)
    cut = int(len(df) * (1 - split_frac))
    return df.iloc[:cut], df.iloc[cut:]


def encode_features(train, test, feature_cols):
    train, test = train.copy(), test.copy()
    for col in feature_cols:
        if not pd.api.types.is_numeric_dtype(train[col]):
            le = LabelEncoder()
            combined = pd.concat([train[col], test[col]]).astype(str).fillna("__missing__")
            le.fit(combined)
            train[col] = le.transform(train[col].astype(str).fillna("__missing__"))
            test[col] = le.transform(test[col].astype(str).fillna("__missing__"))
        else:
            median = train[col].median()
            train[col] = train[col].fillna(median)
            test[col] = test[col].fillna(median)
    return train, test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--target", required=True)
    ap.add_argument("--split-date-col")
    ap.add_argument("--split-frac", type=float, default=0.2)
    ap.add_argument("--sample-rows", type=int, default=200_000)
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    print(f"## baselines: {args.path} [{args.target}]")
    if args.target not in df.columns:
        print(f"- FAILED — target column '{args.target}' not found")
        return
    df = df.dropna(subset=[args.target])

    if args.split_date_col:
        if args.split_date_col not in df.columns:
            print(f"- FAILED — split-date-col '{args.split_date_col}' not found")
            return
        df[args.split_date_col] = pd.to_datetime(df[args.split_date_col], errors="coerce")
        train, test = time_split(df, args.split_date_col, args.split_frac)
        split_note = f"time-based split on {args.split_date_col}"
    else:
        train, test = random_split(df, args.split_frac)
        split_note = "random split — time-based split not requested, verify time doesn't matter here"

    print(f"- split: {split_note} ({len(train)} train / {len(test)} test)")

    y_train_raw, y_test_raw = train[args.target], test[args.target]
    is_classification = not pd.api.types.is_numeric_dtype(y_train_raw) or y_train_raw.nunique() <= 20

    feature_cols = [c for c in df.columns if c not in (args.target, args.split_date_col)]
    if not feature_cols:
        print("- no feature columns available beyond target/date")
        return
    train, test = encode_features(train, test, feature_cols)
    X_train, X_test = train[feature_cols], test[feature_cols]

    if is_classification:
        le = LabelEncoder().fit(pd.concat([y_train_raw, y_test_raw]).astype(str))
        y_train, y_test = le.transform(y_train_raw.astype(str)), le.transform(y_test_raw.astype(str))
        if len(set(y_test)) < 2:
            print("- FAILED — test split has fewer than 2 classes, can't score AUC")
            return

        majority_class = pd.Series(y_train).mode()[0]
        majority_pred = np.full(len(y_test), majority_class)
        majority_auc = roc_auc_score(y_test, majority_pred) if len(set(majority_pred)) > 1 else 0.5
        print(f"- majority-class baseline: AUC={majority_auc:.4g}")

        is_binary = len(set(y_train)) == 2
        if is_binary:
            lr = LogisticRegression(max_iter=1000).fit(X_train, y_train)
            lr_auc = roc_auc_score(y_test, lr.predict_proba(X_test)[:, 1])
            print(f"- logistic regression: AUC={lr_auc:.4g}")

            gbm = GradientBoostingClassifier(random_state=0).fit(X_train, y_train)
            gbm_auc = roc_auc_score(y_test, gbm.predict_proba(X_test)[:, 1])
            print(f"- GBM (default params): AUC={gbm_auc:.4g}")
            best_name, best_score = max(
                [("majority-class", majority_auc), ("logistic regression", lr_auc), ("GBM default", gbm_auc)],
                key=lambda r: r[1],
            )
        else:
            print("- logistic/GBM skipped: >2 classes, multiclass baseline not implemented here — use majority-class as the bar")
            best_name, best_score = "majority-class", majority_auc
        print(f"- bar to beat: AUC={best_score:.4g}, set by {best_name}")
    else:
        y_train, y_test = y_train_raw.values, y_test_raw.values
        mean_pred = np.full(len(y_test), y_train.mean())
        mean_rmse = np.sqrt(np.mean((y_test - mean_pred) ** 2))
        print(f"- mean-predictor baseline: RMSE={mean_rmse:.4g}")

        results = [("mean-predictor", mean_rmse)]
        if args.split_date_col:
            last_value = y_train[-1]
            last_pred = np.full(len(y_test), last_value)
            last_rmse = np.sqrt(np.mean((y_test - last_pred) ** 2))
            print(f"- last-value baseline: RMSE={last_rmse:.4g}")
            results.append(("last-value", last_rmse))

        gbm = GradientBoostingRegressor(random_state=0).fit(X_train, y_train)
        gbm_rmse = np.sqrt(np.mean((y_test - gbm.predict(X_test)) ** 2))
        print(f"- GBM (default params): RMSE={gbm_rmse:.4g}")
        results.append(("GBM default", gbm_rmse))

        best_name, best_score = min(results, key=lambda r: r[1])
        print(f"- bar to beat: RMSE={best_score:.4g}, set by {best_name}")


if __name__ == "__main__":
    main()
