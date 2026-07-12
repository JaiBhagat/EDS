#!/usr/bin/env python3
"""EDS — Model explainability (MVP).

Two modes:
  global — family-level SHAP aggregation over the champion model
  local  — per-prediction reason codes mapped back to FDE catalog rationale

Usage:
    python explain.py global \
        --model-path .eds/models/champion_model.joblib \
        --data-path test_data.csv \
        --catalog-path .eds/features/feature_catalog.json \
        [--out .eds/models/explanation_global.json] [--sample-rows 1000]

    python explain.py local \
        --model-path .eds/models/champion_model.joblib \
        --data-path cases_to_explain.csv \
        --catalog-path .eds/features/feature_catalog.json \
        --top-k 5 \
        [--out .eds/models/reason_codes.csv]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd


def _load_catalog(catalog_path: str) -> dict[str, dict]:
    """Load feature catalog and build a name → entry lookup."""
    if not os.path.exists(catalog_path):
        return {}
    with open(catalog_path) as f:
        entries = json.load(f)
    return {e["name"]: e for e in entries if isinstance(e, dict) and "name" in e}


def _build_family_map(catalog: dict[str, dict], feature_names: list[str]) -> dict[str, str]:
    """Map feature names to their family from the catalog."""
    family_map = {}
    for name in feature_names:
        entry = catalog.get(name, {})
        family_map[name] = entry.get("family", "uncatalogued")
    return family_map


def _get_shap_values(model, X: pd.DataFrame) -> np.ndarray:
    """Compute SHAP values. Falls back to permutation if TreeExplainer isn't applicable."""
    try:
        import shap
    except ImportError:
        print("ERROR: shap package not installed. Run: pip install shap", file=sys.stderr)
        sys.exit(1)

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        # For binary classification, TreeExplainer may return a list [class0, class1]
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # positive class
    except Exception:
        # Fallback to permutation explainer (works for any model)
        explainer = shap.Explainer(model.predict_proba if hasattr(model, "predict_proba") else model.predict, X)
        shap_values = explainer(X).values
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 1]  # positive class

    return np.array(shap_values)


def global_explanation(
    model_path: str,
    data_path: str,
    catalog_path: str,
    out_path: str = ".eds/models/explanation_global.json",
    sample_rows: int = 1000,
) -> dict:
    """Compute family-level SHAP attribution."""
    import joblib

    model = joblib.load(model_path)
    df = pd.read_csv(data_path, nrows=sample_rows)
    catalog = _load_catalog(catalog_path)

    # Determine feature columns (from model if possible, else from data)
    if hasattr(model, "feature_names_in_"):
        feature_names = list(model.feature_names_in_)
    else:
        feature_names = [c for c in df.columns if c in catalog or c not in ("target",)]

    X = df[feature_names].fillna(0)
    shap_values = _get_shap_values(model, X)
    family_map = _build_family_map(catalog, feature_names)

    # Aggregate SHAP by family
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    family_shap: dict[str, float] = {}
    for i, name in enumerate(feature_names):
        family = family_map.get(name, "uncatalogued")
        family_shap[family] = family_shap.get(family, 0.0) + float(mean_abs_shap[i])

    total = sum(family_shap.values())
    family_ranked = sorted(family_shap.items(), key=lambda x: x[1], reverse=True)

    result = {
        "type": "global_family_shap",
        "model_path": model_path,
        "sample_rows": len(X),
        "n_features": len(feature_names),
        "n_families": len(family_shap),
        "families": [
            {
                "family": fam,
                "total_shap": round(val, 6),
                "pct_attribution": round(val / total * 100, 2) if total > 0 else 0,
                "n_features": sum(1 for f in feature_names if family_map.get(f) == fam),
            }
            for fam, val in family_ranked
        ],
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"## Global explanation: {model_path}")
    print(f"- features: {len(feature_names)}, families: {len(family_shap)}")
    print(f"- sample: {len(X)} rows")
    for fam, val in family_ranked[:5]:
        pct = val / total * 100 if total > 0 else 0
        print(f"  {fam}: {pct:.1f}% of total attribution")
    print(f"- output: {out_path}")

    return result


def local_explanation(
    model_path: str,
    data_path: str,
    catalog_path: str,
    top_k: int = 5,
    out_path: str = ".eds/models/reason_codes.csv",
) -> pd.DataFrame:
    """Compute per-prediction reason codes mapped to catalog rationales."""
    import joblib

    model = joblib.load(model_path)
    df = pd.read_csv(data_path)
    catalog = _load_catalog(catalog_path)

    if hasattr(model, "feature_names_in_"):
        feature_names = list(model.feature_names_in_)
    else:
        feature_names = [c for c in df.columns if c in catalog or c not in ("target",)]

    X = df[feature_names].fillna(0)
    shap_values = _get_shap_values(model, X)

    rows = []
    for i in range(len(X)):
        sv = shap_values[i]
        top_indices = np.argsort(np.abs(sv))[::-1][:top_k]

        reasons = []
        for rank, idx in enumerate(top_indices, 1):
            feat_name = feature_names[idx]
            entry = catalog.get(feat_name, {})
            rationale = entry.get("rationale", entry.get("evidence", f"feature: {feat_name}"))
            family = entry.get("family", "uncatalogued")
            reasons.append({
                "rank": rank,
                "feature": feat_name,
                "family": family,
                "shap_value": round(float(sv[idx]), 6),
                "direction": "increases" if sv[idx] > 0 else "decreases",
                "reason": f"{rationale} ({family} family)",
            })

        row = {"row_index": i}
        for r in reasons:
            prefix = f"reason_{r['rank']}"
            row[f"{prefix}_feature"] = r["feature"]
            row[f"{prefix}_shap"] = r["shap_value"]
            row[f"{prefix}_direction"] = r["direction"]
            row[f"{prefix}_text"] = r["reason"]
        rows.append(row)

    result_df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    result_df.to_csv(out_path, index=False)

    print(f"## Local explanation: {model_path}")
    print(f"- predictions explained: {len(result_df)}")
    print(f"- top-k reasons per prediction: {top_k}")
    print(f"- output: {out_path}")

    return result_df


def main() -> None:
    ap = argparse.ArgumentParser(description="Model explainability (MVP)")
    sub = ap.add_subparsers(dest="cmd")

    gl = sub.add_parser("global", help="Family-level SHAP aggregation")
    gl.add_argument("--model-path", required=True)
    gl.add_argument("--data-path", required=True)
    gl.add_argument("--catalog-path", default=".eds/features/feature_catalog.json")
    gl.add_argument("--out", default=".eds/models/explanation_global.json")
    gl.add_argument("--sample-rows", type=int, default=1000)

    lo = sub.add_parser("local", help="Per-prediction reason codes")
    lo.add_argument("--model-path", required=True)
    lo.add_argument("--data-path", required=True)
    lo.add_argument("--catalog-path", default=".eds/features/feature_catalog.json")
    lo.add_argument("--top-k", type=int, default=5)
    lo.add_argument("--out", default=".eds/models/reason_codes.csv")

    args = ap.parse_args()

    if args.cmd == "global":
        global_explanation(
            args.model_path, args.data_path, args.catalog_path,
            out_path=args.out, sample_rows=args.sample_rows,
        )
    elif args.cmd == "local":
        local_explanation(
            args.model_path, args.data_path, args.catalog_path,
            top_k=args.top_k, out_path=args.out,
        )
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
