#!/usr/bin/env python3
"""Wide-table column triage — makes 2000+ columns *discussable* before FDE.

Produces a per-column triage table with dtype, null rate, cardinality,
constant/duplicate flags, univariate signal vs. target, and a suggested
triage bucket:

- DROP-CANDIDATE:     constant, >95% null, or exact duplicate
- HIGH-SIGNAL:        top decile of univariate signal
- NEEDS-DOMAIN-INPUT: non-trivial signal but opaque name → surface to human
- LOW-PRIORITY:       everything else

CRITICAL: this skill NEVER drops anything. It buckets and reports; the human
and the FDE funnel decide. An automated 2000→50 cut with no conversation is
exactly what the user does not want.

Usage:
    python column_triage.py <path.csv> --target <col> \
        [--source-label main] [--out .eds/data/column_triage.csv]
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd


# Names that look self-documenting (not needing domain input)
READABLE_NAME_PATTERNS = [
    "age", "amount", "balance", "count", "date", "duration", "fee",
    "income", "length", "month", "number", "payment", "percent",
    "price", "rate", "ratio", "revenue", "salary", "score", "sum",
    "time", "total", "value", "volume", "weight", "year",
]


def _is_opaque_name(col_name: str) -> bool:
    """Heuristic: column name that's likely opaque without domain context."""
    name = col_name.lower()
    # Short or numeric-looking names
    if len(name) <= 3:
        return True
    if name.startswith("col") or name.startswith("var") or name.startswith("x"):
        return True
    # Check if any readable pattern appears
    return not any(pat in name for pat in READABLE_NAME_PATTERNS)


def triage_columns(
    df: pd.DataFrame,
    target: str,
    source_label: str = "main",
    near_constant_frac: float = 0.99,
    high_null_frac: float = 0.95,
) -> pd.DataFrame:
    """Compute triage table for all columns except the target.

    Returns a DataFrame with one row per column and triage metadata.
    """
    from sklearn.metrics import roc_auc_score

    cols = [c for c in df.columns if c != target]
    y = df[target]
    is_binary = pd.api.types.is_numeric_dtype(y) and y.nunique() == 2
    positive_rate = float(y.mean()) if is_binary and y.min() == 0 else None

    # Precompute duplicate hashes for all columns
    hashes: dict[str, int] = {}
    dup_map: dict[str, str] = {}
    for col in cols:
        h = int(pd.util.hash_pandas_object(df[col].fillna("__NA__")).sum())
        for prev_col, prev_h in hashes.items():
            if h == prev_h:
                dup_map[col] = prev_col
                break
        hashes[col] = h

    rows = []
    signals: dict[str, float] = {}

    for col in cols:
        s = df[col]
        null_rate = float(s.isna().mean())
        is_numeric = pd.api.types.is_numeric_dtype(s)
        cardinality = int(s.nunique(dropna=True))
        dtype_str = str(s.dtype)

        # Constant check
        top_frac = float(s.value_counts(normalize=True, dropna=False).iloc[0]) if len(s) else 1.0
        is_constant = top_frac >= near_constant_frac

        # Duplicate check
        is_dup = col in dup_map

        # Univariate signal
        signal = 0.0
        if is_numeric and is_binary and null_rate < high_null_frac:
            try:
                x = s.fillna(s.median())
                auc = roc_auc_score(y, x)
                signal = float(abs(auc - 0.5) * 2)  # normalized to [0, 1]
            except (ValueError, TypeError):
                signal = 0.0
        elif is_numeric and pd.api.types.is_numeric_dtype(y):
            corr = s.corr(y)
            signal = float(abs(corr)) if pd.notna(corr) else 0.0

        signals[col] = signal

        rows.append({
            "column": col,
            "source": source_label,
            "dtype": dtype_str,
            "null_rate": round(null_rate, 4),
            "cardinality": cardinality,
            "is_constant": is_constant,
            "is_duplicate_of": dup_map.get(col, ""),
            "univariate_signal": round(signal, 4),
        })

    result = pd.DataFrame(rows)

    # Assign triage buckets
    if not result.empty:
        signal_threshold = result["univariate_signal"].quantile(0.9)
        buckets = []
        for _, row in result.iterrows():
            if row["is_constant"] or row["null_rate"] >= high_null_frac or row["is_duplicate_of"]:
                buckets.append("DROP-CANDIDATE")
            elif row["univariate_signal"] >= signal_threshold and signal_threshold > 0:
                buckets.append("HIGH-SIGNAL")
            elif row["univariate_signal"] > 0.01 and _is_opaque_name(row["column"]):
                buckets.append("NEEDS-DOMAIN-INPUT")
            else:
                buckets.append("LOW-PRIORITY")
        result["triage_bucket"] = buckets

    return result


def write_summary(triage_df: pd.DataFrame, out_path: str) -> str:
    """Write markdown summary alongside the CSV."""
    summary_path = out_path.replace(".csv", "_summary.md")
    bucket_counts = triage_df["triage_bucket"].value_counts()
    lines = [
        "# Column Triage Summary\n",
        f"\nTotal columns: {len(triage_df)}\n",
        "\n## Bucket distribution\n",
    ]
    for bucket in ["DROP-CANDIDATE", "HIGH-SIGNAL", "NEEDS-DOMAIN-INPUT", "LOW-PRIORITY"]:
        count = bucket_counts.get(bucket, 0)
        lines.append(f"- **{bucket}**: {count}\n")

    needs_input = triage_df[triage_df["triage_bucket"] == "NEEDS-DOMAIN-INPUT"]
    if not needs_input.empty:
        lines.append("\n## Columns needing domain input\n\n")
        lines.append("These columns have non-trivial signal but opaque names — surface them to the human:\n\n")
        for _, row in needs_input.head(20).iterrows():
            lines.append(f"- `{row['column']}` (signal={row['univariate_signal']:.3f}, "
                         f"null={row['null_rate']:.0%}, source={row['source']})\n")

    drop = triage_df[triage_df["triage_bucket"] == "DROP-CANDIDATE"]
    if not drop.empty:
        lines.append(f"\n## DROP-CANDIDATE columns ({len(drop)})\n\n")
        for _, row in drop.head(10).iterrows():
            reason = "constant" if row["is_constant"] else (
                f"dup of {row['is_duplicate_of']}" if row["is_duplicate_of"] else
                f"null {row['null_rate']:.0%}")
            lines.append(f"- `{row['column']}` — {reason}\n")

    with open(summary_path, "w") as f:
        f.writelines(lines)
    return summary_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Wide-table column triage")
    ap.add_argument("path", help="CSV file to triage")
    ap.add_argument("--target", required=True, help="Target column name")
    ap.add_argument("--source-label", default="main", help="Source table label")
    ap.add_argument("--out", default=".eds/data/column_triage.csv",
                    help="Output CSV path")
    ap.add_argument("--sample-rows", type=int, default=50_000,
                    help="Max rows to sample for triage")
    args = ap.parse_args()

    df = pd.read_csv(args.path, nrows=args.sample_rows)
    if args.target not in df.columns:
        print(f"FAILED — target column '{args.target}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"## column triage: {args.path}")
    print(f"- columns: {len(df.columns) - 1} (excluding target)")
    print(f"- rows sampled: {len(df)}")

    result = triage_columns(df, args.target, source_label=args.source_label)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    result.to_csv(args.out, index=False)
    print(f"- triage table: {args.out}")

    summary_path = write_summary(result, args.out)
    print(f"- summary: {summary_path}")

    bucket_counts = result["triage_bucket"].value_counts()
    for bucket in ["DROP-CANDIDATE", "HIGH-SIGNAL", "NEEDS-DOMAIN-INPUT", "LOW-PRIORITY"]:
        count = bucket_counts.get(bucket, 0)
        print(f"  {bucket}: {count}")


if __name__ == "__main__":
    main()
