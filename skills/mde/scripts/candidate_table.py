#!/usr/bin/env python3
"""MDE — Candidate strategy table.

Manages the ordered list of modeling approaches to try. The baseline is
always the reigning champion (M1). Candidates are added based on error
analysis diagnosis, not random search — diagnosis earns the right to search.

Usage:
    python candidate_table.py init --task-type classification \
        [--out .eds/models/candidate_table.json]

    python candidate_table.py add --name "RF tuned" --model-type RandomForest \
        --rationale "Error analysis shows high-variance errors — try bagging" \
        [--table-path .eds/models/candidate_table.json]

    python candidate_table.py show [--table-path .eds/models/candidate_table.json]
"""
import argparse
import json
import os
from datetime import datetime, timezone

# Standard candidate sets by task type — baseline always first
STANDARD_CANDIDATES = {
    "classification": [
        {
            "name": "majority-class",
            "model_type": "DummyClassifier",
            "rationale": "Lower bound — any real model must beat this",
            "params": {"strategy": "most_frequent"},
            "stage": "baseline",
        },
        {
            "name": "logistic-regression",
            "model_type": "LogisticRegression",
            "rationale": "Linear baseline — if this suffices, nothing more complex is needed (rung 6)",
            "params": {"max_iter": 1000, "random_state": 42},
            "stage": "baseline",
        },
        {
            "name": "gbm-default",
            "model_type": "GradientBoostingClassifier",
            "rationale": "Standard non-linear baseline with default hyperparameters",
            "params": {"n_estimators": 100, "max_depth": 3, "random_state": 42},
            "stage": "baseline",
        },
    ],
    "regression": [
        {
            "name": "mean-predictor",
            "model_type": "DummyRegressor",
            "rationale": "Lower bound — predicts the training mean",
            "params": {"strategy": "mean"},
            "stage": "baseline",
        },
        {
            "name": "linear-regression",
            "model_type": "Ridge",
            "rationale": "Linear baseline with regularization (rung 6)",
            "params": {"alpha": 1.0},
            "stage": "baseline",
        },
        {
            "name": "gbm-default",
            "model_type": "GradientBoostingRegressor",
            "rationale": "Standard non-linear baseline with default hyperparameters",
            "params": {"n_estimators": 100, "max_depth": 3, "random_state": 42},
            "stage": "baseline",
        },
    ],
}


def init_table(task_type, out_path):
    """Create initial candidate table with standard baselines."""
    candidates = STANDARD_CANDIDATES.get(task_type, STANDARD_CANDIDATES["classification"])
    table = {
        "task_type": task_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [
            {**c, "status": "pending", "added_at": datetime.now(timezone.utc).isoformat()}
            for c in candidates
        ],
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(table, f, indent=2)
    print(f"Candidate table initialized: {len(candidates)} baselines for {task_type}")
    return table


def add_candidate(table_path, name, model_type, rationale, params=None, stage="candidate"):
    """Add a candidate to the strategy table. Requires a rationale."""
    with open(table_path) as f:
        table = json.load(f)

    entry = {
        "name": name,
        "model_type": model_type,
        "rationale": rationale,
        "params": params or {},
        "stage": stage,
        "status": "pending",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    table["candidates"].append(entry)
    with open(table_path, "w") as f:
        json.dump(table, f, indent=2)
    print(f"Added candidate: {name} ({model_type}) — {rationale[:60]}")
    return entry


def mark_candidate(table_path, name, status, metric_value=None):
    """Mark a candidate as evaluated/rejected/champion."""
    with open(table_path) as f:
        table = json.load(f)

    for c in table["candidates"]:
        if c["name"] == name:
            c["status"] = status
            if metric_value is not None:
                c["metric_value"] = metric_value
            break

    with open(table_path, "w") as f:
        json.dump(table, f, indent=2)


def show_table(table_path):
    """Display the candidate table."""
    with open(table_path) as f:
        table = json.load(f)

    print(f"Task: {table['task_type']} | {len(table['candidates'])} candidates")
    print(f"{'Name':<25} {'Type':<22} {'Stage':<12} {'Status':<10} {'Score':>8}")
    print("-" * 80)
    for c in table["candidates"]:
        name = c["name"][:24]
        mtype = c["model_type"][:21]
        stage = c.get("stage", "?")[:11]
        status = c["status"][:9]
        score = c.get("metric_value", "")
        score_str = f"{score:>8.4f}" if isinstance(score, (int, float)) else f"{'':>8}"
        print(f"{name:<25} {mtype:<22} {stage:<12} {status:<10} {score_str}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    init_cmd = sub.add_parser("init")
    init_cmd.add_argument("--task-type", required=True, choices=["classification", "regression"])
    init_cmd.add_argument("--out", default=".eds/models/candidate_table.json")

    add_cmd = sub.add_parser("add")
    add_cmd.add_argument("--name", required=True)
    add_cmd.add_argument("--model-type", required=True)
    add_cmd.add_argument("--rationale", required=True)
    add_cmd.add_argument("--params", default="{}")
    add_cmd.add_argument("--stage", default="candidate")
    add_cmd.add_argument("--table-path", default=".eds/models/candidate_table.json")

    show_cmd = sub.add_parser("show")
    show_cmd.add_argument("--table-path", default=".eds/models/candidate_table.json")

    args = ap.parse_args()

    if args.cmd == "init":
        init_table(args.task_type, args.out)
    elif args.cmd == "add":
        add_candidate(args.table_path, args.name, args.model_type,
                      args.rationale, json.loads(args.params), args.stage)
    elif args.cmd == "show":
        show_table(args.table_path)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
