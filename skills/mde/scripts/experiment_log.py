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


def load_contract_metric(contract_path=".eds/models/validation_contract.json"):
    """Read the metric from the validation contract."""
    if not os.path.exists(contract_path):
        return None
    with open(contract_path) as f:
        return json.load(f).get("metric")


def log_experiment(log_path, name, model_type, params, metric_name,
                   metric_value, contract_hash, seed=None,
                   train_time_s=None, notes=None, feature_set=None,
                   fold_scores=None, override_metric=None):
    """Append an experiment entry to the log.

    Validates metric_name against the contract metric. Refuses mismatches
    unless override_metric is provided (with a reason string).
    """
    # Validate metric against contract
    contract_metric = load_contract_metric()
    if contract_metric and metric_name != contract_metric:
        if not override_metric:
            raise ValueError(
                f"metric_name '{metric_name}' != contract metric '{contract_metric}'. "
                f"Pass --override-metric '<reason>' to log a non-contract metric."
            )
        # Store the override reason
        notes = (notes or "") + f" [metric-override: {override_metric}]"

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
    log_cmd.add_argument("--metric-name", default=None,
                         help="Metric name (reads from contract if not specified)")
    log_cmd.add_argument("--metric-value", type=float, required=True)
    log_cmd.add_argument("--contract-hash", required=True)
    log_cmd.add_argument("--seed", type=int)
    log_cmd.add_argument("--train-time-s", type=float)
    log_cmd.add_argument("--notes")
    log_cmd.add_argument("--override-metric", default=None,
                         help="Reason for using a non-contract metric (bypasses validation)")
    log_cmd.add_argument("--log-path", default=".eds/models/experiment_log.json")

    show_cmd = sub.add_parser("show")
    show_cmd.add_argument("--log-path", default=".eds/models/experiment_log.json")

    args = ap.parse_args()

    if args.cmd == "log":
        # Resolve metric: explicit > contract > fallback
        metric_name = args.metric_name
        if not metric_name:
            metric_name = load_contract_metric() or "roc_auc"
        try:
            entry = log_experiment(
                args.log_path, args.name, args.model_type,
                args.params, metric_name, args.metric_value,
                args.contract_hash, seed=args.seed,
                train_time_s=args.train_time_s, notes=args.notes,
                override_metric=args.override_metric,
            )
        except ValueError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Logged: {entry['name']} — {entry['metric_name']}={entry['metric_value']:.4f}")

    elif args.cmd == "show":
        show_log(args.log_path)

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
