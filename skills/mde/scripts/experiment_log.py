#!/usr/bin/env python3
"""MDE — Experiment log management.

Every model fit is logged: what was tried, what it scored, under which
contract. The log is append-only and is the single source of truth for
"what have we tried". The champion is selected FROM the log, never outside it.

Usage:
    python experiment_log.py log --name <name> --model-type <type> \
        --params '{"n_estimators": 100}' --metric-value 0.82 \
        --contract-hash abc123 [--log-path .eds/models/experiment_log.json]

    python experiment_log.py show [--log-path .eds/models/experiment_log.json]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone


def load_log(path):
    if not os.path.exists(path):
        return {"experiments": []}
    with open(path) as f:
        return json.load(f)


def save_log(log, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(log, f, indent=2)


def log_experiment(log_path, name, model_type, params, metric_name,
                   metric_value, contract_hash, seed=None,
                   train_time_s=None, notes=None, feature_set=None,
                   fold_scores=None):
    """Append an experiment entry to the log."""
    log = load_log(log_path)

    entry = {
        "name": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_type": model_type,
        "params": params if isinstance(params, dict) else json.loads(params),
        "metric_name": metric_name,
        "metric_value": metric_value,
        "contract_hash": contract_hash,
        "seed": seed,
        "train_time_s": train_time_s,
        "feature_set": feature_set,
        "fold_scores": fold_scores,
        "notes": notes,
    }
    log["experiments"].append(entry)
    save_log(log, log_path)
    return entry


def get_champion(log_path, metric_name=None, higher_is_better=True):
    """Select the best experiment by metric value."""
    log = load_log(log_path)
    experiments = log.get("experiments", [])
    if not experiments:
        return None

    if metric_name:
        experiments = [e for e in experiments if e.get("metric_name") == metric_name]
    if not experiments:
        return None

    key = lambda e: e.get("metric_value", float("-inf"))
    if higher_is_better:
        return max(experiments, key=key)
    return min(experiments, key=key)


def show_log(log_path):
    """Print a summary table of all experiments."""
    log = load_log(log_path)
    experiments = log.get("experiments", [])
    if not experiments:
        print("No experiments logged.")
        return

    print(f"{'Name':<25} {'Type':<20} {'Metric':<12} {'Value':>8} {'Contract':>10}")
    print("-" * 80)
    for e in experiments:
        name = e.get("name", "?")[:24]
        mtype = e.get("model_type", "?")[:19]
        mname = e.get("metric_name", "?")[:11]
        mval = e.get("metric_value", 0)
        chash = e.get("contract_hash", "?")[:9]
        print(f"{name:<25} {mtype:<20} {mname:<12} {mval:>8.4f} {chash:>10}")

    best = get_champion(log_path)
    if best:
        print(f"\nCurrent best: {best['name']} ({best['metric_name']}={best['metric_value']:.4f})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    log_cmd = sub.add_parser("log")
    log_cmd.add_argument("--name", required=True)
    log_cmd.add_argument("--model-type", required=True)
    log_cmd.add_argument("--params", default="{}")
    log_cmd.add_argument("--metric-name", default="roc_auc")
    log_cmd.add_argument("--metric-value", type=float, required=True)
    log_cmd.add_argument("--contract-hash", required=True)
    log_cmd.add_argument("--seed", type=int)
    log_cmd.add_argument("--train-time-s", type=float)
    log_cmd.add_argument("--notes")
    log_cmd.add_argument("--log-path", default=".eds/models/experiment_log.json")

    show_cmd = sub.add_parser("show")
    show_cmd.add_argument("--log-path", default=".eds/models/experiment_log.json")

    args = ap.parse_args()

    if args.cmd == "log":
        entry = log_experiment(
            args.log_path, args.name, args.model_type,
            args.params, args.metric_name, args.metric_value,
            args.contract_hash, seed=args.seed,
            train_time_s=args.train_time_s, notes=args.notes,
        )
        print(f"Logged: {entry['name']} — {entry['metric_name']}={entry['metric_value']:.4f}")

    elif args.cmd == "show":
        show_log(args.log_path)

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
