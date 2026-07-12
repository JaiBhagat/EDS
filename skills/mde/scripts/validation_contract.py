#!/usr/bin/env python3
"""MDE — Validation contract management.

The validation contract defines HOW a model gets evaluated: metric, split
strategy, seed, and constraints. It's written once at the start of modeling
and never silently modified — the hash locks it. A wrong split invalidates
everything downstream (M4), so this is highest leverage.

Usage:
    python validation_contract.py create <path.csv> --target <col> \
        [--time-col <col>] [--entity-col <col>] [--metric auto] \
        [--out .eds/models/validation_contract.json]

    python validation_contract.py verify .eds/models/validation_contract.json
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def detect_task_type(df, target):
    y = df[target]
    if not pd.api.types.is_numeric_dtype(y) or y.nunique() <= 20:
        return "classification"
    return "regression"


def detect_split_strategy(df, time_col=None, entity_col=None):
    """Auto-select the safest split strategy."""
    if time_col and time_col in df.columns:
        if entity_col and entity_col in df.columns:
            return "temporal-entity-aware"
        return "temporal"
    if entity_col and entity_col in df.columns:
        return "entity-grouped"
    return "random"


def read_brief_metric(brief_path: str = ".eds/BRIEF.md") -> str | None:
    """Parse the primary metric from the Brief's Stage 5 section."""
    import re
    if not os.path.exists(brief_path):
        return None
    with open(brief_path) as f:
        content = f.read()
    # Look for "Primary metric" in Stage 5 or metric table
    patterns = [
        r"[Pp]rimary\s+metric[:\s]+[`\"]?(\w+)[`\"]?",
        r"\|\s*metric\s*\|\s*[`\"]?(\w+)[`\"]?",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return m.group(1)
    return None


def select_metric(task_type: str, brief_metric: str | None = None,
                  positive_rate: float | None = None) -> tuple[str, str]:
    """Choose metric matched to task type. Returns (metric, reason).

    Priority: explicit brief_metric > imbalance-aware default > generic default.
    """
    if brief_metric:
        return brief_metric, f"Brief specifies '{brief_metric}'"

    if task_type == "classification":
        if positive_rate is not None and positive_rate < 0.02:
            return ("average_precision",
                    f"Positive rate {positive_rate:.4f} < 2% — AUC is insensitive "
                    "to performance on the minority class; AUPRC is the honest metric")
        return "roc_auc", "AUC: threshold-invariant, suitable when cost asymmetry hasn't pinned an operating point yet"
    return "neg_rmse", "RMSE: penalizes large errors more than MAE, appropriate for most regression tasks"


def compute_hash(contract):
    """Deterministic hash of the contract for tamper detection."""
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def create_contract(df, target, time_col=None, entity_col=None,
                    metric=None, seed=42, n_folds=5, holdout_frac=0.15,
                    brief_path=".eds/BRIEF.md"):
    """Build a validation contract from data characteristics."""
    task_type = detect_task_type(df, target)
    split_strategy = detect_split_strategy(df, time_col, entity_col)

    # Metric resolution: explicit arg > Brief > imbalance-aware default
    explicit_metric = metric if metric and metric != "auto" else None
    brief_metric = None if explicit_metric else read_brief_metric(brief_path)
    resolved_source = explicit_metric or brief_metric

    # Compute positive rate for imbalance-aware default
    positive_rate = None
    if task_type == "classification" and not resolved_source:
        y = df[target]
        if pd.api.types.is_numeric_dtype(y) and y.nunique() == 2:
            positive_rate = float(y.mean()) if y.min() == 0 else float((y == y.value_counts().idxmin()).mean())

    chosen_metric, metric_reason = select_metric(
        task_type, resolved_source, positive_rate
    )

    contract = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_type": task_type,
        "target": target,
        "metric": chosen_metric,
        "metric_source": "brief" if brief_metric else ("user" if explicit_metric else "auto"),
        "split_strategy": split_strategy,
        "time_col": time_col,
        "entity_col": entity_col,
        "seed": seed,
        "n_folds": n_folds,
        "holdout_frac": holdout_frac,
        "constraints": {
            "max_train_time_seconds": None,
            "max_model_size_mb": None,
            "interpretability_required": False,
        },
        "rationale": {
            "split_reason": _split_rationale(split_strategy, time_col, entity_col),
            "metric_reason": metric_reason,
        },
    }
    if positive_rate is not None:
        contract["positive_rate"] = round(positive_rate, 6)
    # Hash covers everything except the hash field itself
    contract["hash"] = compute_hash(contract)
    return contract


def _split_rationale(strategy, time_col, entity_col):
    if strategy == "temporal-entity-aware":
        return (f"Time column '{time_col}' present + entity column '{entity_col}' — "
                "temporal split with entity grouping prevents both future leakage "
                "and entity contamination across folds")
    if strategy == "temporal":
        return (f"Time column '{time_col}' present — temporal split prevents "
                "future-into-past leakage (A4)")
    if strategy == "entity-grouped":
        return (f"Entity column '{entity_col}' present — grouped split prevents "
                "same entity appearing in both train and test")
    return "No time or entity column specified — using random split. Verify time doesn't matter."


def _metric_rationale(metric, task_type):
    """Fallback rationale lookup — only used if select_metric didn't provide one."""
    rationales = {
        "roc_auc": "AUC: threshold-invariant, suitable when cost asymmetry hasn't pinned an operating point yet",
        "average_precision": "AUPRC: honest metric for imbalanced classification where positives are rare",
        "neg_rmse": "RMSE: penalizes large errors more than MAE, appropriate for most regression tasks",
        "precision_at_k": "Precision@k: matched to a fixed review capacity",
        "f1": "F1: harmonic mean when FP and FN are roughly equally costly",
        "neg_mae": "MAE: robust to outliers when large errors aren't disproportionately costly",
    }
    return rationales.get(metric, f"User-specified metric: {metric}")


def verify_contract(contract_path):
    """Verify a contract file is intact (hash matches)."""
    with open(contract_path) as f:
        contract = json.load(f)

    stored_hash = contract.pop("hash", None)
    computed_hash = compute_hash(contract)
    contract["hash"] = stored_hash  # restore

    if stored_hash != computed_hash:
        return False, f"Hash mismatch: stored={stored_hash}, computed={computed_hash}"
    return True, f"Contract intact (hash={stored_hash})"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    create = sub.add_parser("create")
    create.add_argument("path")
    create.add_argument("--target", required=True)
    create.add_argument("--time-col")
    create.add_argument("--entity-col")
    create.add_argument("--metric", default="auto")
    create.add_argument("--seed", type=int, default=42)
    create.add_argument("--out", default=".eds/models/validation_contract.json")

    verify = sub.add_parser("verify")
    verify.add_argument("path")

    args = ap.parse_args()

    if args.cmd == "create":
        df = pd.read_csv(args.path, nrows=50_000)
        contract = create_contract(
            df, args.target,
            time_col=args.time_col,
            entity_col=args.entity_col,
            metric=args.metric if args.metric != "auto" else None,
            seed=args.seed,
        )
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(contract, f, indent=2)
        print(f"Validation contract written to {args.out}")
        print(f"  task: {contract['task_type']}, metric: {contract['metric']}")
        print(f"  split: {contract['split_strategy']}, seed: {contract['seed']}")
        print(f"  hash: {contract['hash']}")

    elif args.cmd == "verify":
        ok, msg = verify_contract(args.path)
        print(f"{'PASS' if ok else 'FAIL'}: {msg}")
        sys.exit(0 if ok else 1)

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
