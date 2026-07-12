#!/usr/bin/env python3
"""EDA figure generation — class-conditional overlays and correlation heatmap.

Usage:
    python eda_figures.py <path.csv> --target <col> \
        --features feat1,feat2,feat3 \
        [--out-dir .eds/eda/figures/] [--sample-rows 50000]
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd


def plot_class_conditional(df: pd.DataFrame, feature: str, target: str,
                           out_dir: str) -> str:
    """Generate a class-conditional violin/box plot for a feature."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))

    classes = sorted(df[target].unique())
    data = [df[df[target] == c][feature].dropna().values for c in classes]
    labels = [f"{target}={c}" for c in classes]

    # Violin plot with box overlay
    parts = ax.violinplot(data, positions=range(len(classes)), showmedians=True)
    for pc in parts.get("bodies", []):
        pc.set_alpha(0.5)

    # Add median annotations
    for i, d in enumerate(data):
        if len(d) > 0:
            median = np.median(d)
            ax.annotate(f"med={median:.3g}", xy=(i, median),
                        xytext=(i + 0.3, median), fontsize=9, color="red")

    ax.set_xticks(range(len(classes)))
    ax.set_xticklabels(labels)
    ax.set_ylabel(feature)
    ax.set_title(f"{feature} by {target}")
    ax.grid(axis="y", alpha=0.3)

    out_path = os.path.join(out_dir, f"class_conditional_{feature}.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_correlation_heatmap(df: pd.DataFrame, features: list[str],
                             out_dir: str) -> str:
    """Generate a correlation heatmap of the feature set."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    corr = df[features].corr()
    n = len(features)

    fig_size = max(8, n * 0.5)
    fig, ax = plt.subplots(1, 1, figsize=(fig_size, fig_size))

    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    fig.colorbar(im, ax=ax, shrink=0.8)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(features, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(features, fontsize=8)
    ax.set_title("Feature Correlation Matrix")

    # Annotate high correlations
    for i in range(n):
        for j in range(n):
            if i != j and abs(corr.iloc[i, j]) > 0.7:
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}",
                        ha="center", va="center", fontsize=7, color="white")

    out_path = os.path.join(out_dir, "correlation_heatmap.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Generate EDA figures")
    ap.add_argument("path")
    ap.add_argument("--target", required=True)
    ap.add_argument("--features", required=True,
                    help="Comma-separated list of top-signal features")
    ap.add_argument("--out-dir", default=".eds/eda/figures/")
    ap.add_argument("--sample-rows", type=int, default=50_000)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    features = [f.strip() for f in args.features.split(",")]

    # Validate columns exist
    missing = [f for f in features + [args.target] if f not in df.columns]
    if missing:
        print(f"FAILED: columns not found: {missing}", file=sys.stderr)
        sys.exit(1)

    print(f"## EDA Figures: {args.path}")
    print(f"- target: {args.target}")
    print(f"- features: {features}")

    # Class-conditional plots for each feature
    for feat in features:
        if pd.api.types.is_numeric_dtype(df[feat]):
            path = plot_class_conditional(df, feat, args.target, args.out_dir)
            print(f"- class_conditional_{feat}.png: saved")
        else:
            print(f"- {feat}: skipped (non-numeric)")

    # Correlation heatmap
    numeric_features = [f for f in features if pd.api.types.is_numeric_dtype(df[f])]
    if len(numeric_features) >= 2:
        path = plot_correlation_heatmap(df, numeric_features, args.out_dir)
        print(f"- correlation_heatmap.png: saved")

    print(f"\nFigures written to: {args.out_dir}")


if __name__ == "__main__":
    main()
