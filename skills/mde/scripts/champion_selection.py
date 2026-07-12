#!/usr/bin/env python3
"""MDE — Champion selection via Pareto front + SE-floor stopping.

Selects the champion from the experiment log using Pareto-optimal
selection (performance vs. complexity) with SE-floor stopping for HPO.
The champion ships with a monitoring contract.

Usage:
    python champion_selection.py select \
        --log-path .eds/models/experiment_log.json \
        --contract-path .eds/models/validation_contract.json \
        [--out .eds/models/champion.json]

    python champion_selection.py monitoring-contract \
        --champion-path .eds/models/champion.json \
        [--out .eds/models/monitoring_contract.json]
"""
import argparse
import json
import os
from datetime import datetime, timezone


# Complexity proxy by model type
COMPLEXITY_ORDER = {
    "DummyClassifier": 1, "DummyRegressor": 1,
    "LogisticRegression": 2, "Ridge": 2, "Lasso": 2,
    "LinearRegression": 2, "SGDClassifier": 2,
    "DecisionTreeClassifier": 3, "DecisionTreeRegressor": 3,
    "RandomForestClassifier": 4, "RandomForestRegressor": 4,
    "GradientBoostingClassifier": 5, "GradientBoostingRegressor": 5,
    "XGBClassifier": 5, "XGBRegressor": 5,
    "LGBMClassifier": 5, "LGBMRegressor": 5,
    "CatBoostClassifier": 5, "CatBoostRegressor": 5,
    "MLPClassifier": 6, "MLPRegressor": 6,
}


def get_complexity(model_type):
    return COMPLEXITY_ORDER.get(model_type, 7)


def pareto_front(experiments, higher_is_better=True):
    """Return the Pareto-optimal experiments (maximize metric, minimize complexity)."""
    if not experiments:
        return []

    sorted_exps = sorted(
        experiments,
        key=lambda e: (
            e.get("metric_value", float("-inf")) if higher_is_better
            else -e.get("metric_value", float("inf")),
            -get_complexity(e.get("model_type", ""))
        ),
        reverse=True,
    )

    front = []
    best_complexity = float("inf")
    for exp in sorted_exps:
        complexity = get_complexity(exp.get("model_type", ""))
        if complexity < best_complexity:
            front.append(exp)
            best_complexity = complexity

    return front


def se_floor_check(experiments, se_threshold=0.5):
    """Check if further HPO is likely to help.

    If the best model's improvement over the second-best is less than
    se_threshold * SE of the best model's fold scores, further tuning
    is unlikely to yield meaningful gains.
    """
    if len(experiments) < 2:
        return True, "too few experiments to judge"

    sorted_exps = sorted(experiments, key=lambda e: e.get("metric_value", 0), reverse=True)
    best = sorted_exps[0]
    second = sorted_exps[1]

    fold_scores = best.get("fold_scores")
    if not fold_scores or len(fold_scores) < 2:
        return True, "no fold scores available for SE calculation"

    import numpy as np
    se = np.std(fold_scores, ddof=1) / np.sqrt(len(fold_scores))
    gap = abs(best.get("metric_value", 0) - second.get("metric_value", 0))

    if gap < se_threshold * se:
        return False, (
            f"gap between top-2 ({gap:.4f}) < {se_threshold}*SE ({se_threshold * se:.4f}) "
            f"— further HPO unlikely to help materially"
        )
    return True, f"gap ({gap:.4f}) > {se_threshold}*SE ({se_threshold * se:.4f}) — room to improve"


def select_champion(log_path, contract_path, higher_is_better=True):
    """Select champion from experiment log using Pareto + parsimony."""
    with open(log_path) as f:
        log = json.load(f)
    with open(contract_path) as f:
        contract = json.load(f)

    experiments = log.get("experiments", [])
    if not experiments:
        return None

    # Filter to experiments matching current contract hash
    contract_hash = contract.get("hash")
    if contract_hash:
        valid = [e for e in experiments if e.get("contract_hash") == contract_hash]
        if not valid:
            valid = experiments  # fallback if no hash match
    else:
        valid = experiments

    # 1-SE rule: among models within 1 SE of the best, pick the simplest.
    # This is the standard parsimony heuristic — a simpler model wins only
    # when the metric gap is within noise.
    import numpy as np

    sorted_valid = sorted(valid, key=lambda e: e.get("metric_value", float("-inf")), reverse=higher_is_better)
    best = sorted_valid[0]
    best_score = best.get("metric_value", 0)

    # Compute SE from the best model's fold scores, or use a default
    fold_scores = best.get("fold_scores")
    if fold_scores and len(fold_scores) >= 2:
        se = float(np.std(fold_scores, ddof=1) / np.sqrt(len(fold_scores)))
    else:
        se = abs(best_score) * 0.02  # fallback: 2% of best score

    # Models within 1 SE of the best
    threshold = best_score - se if higher_is_better else best_score + se
    within_se = [
        e for e in sorted_valid
        if (e.get("metric_value", float("-inf")) >= threshold if higher_is_better
            else e.get("metric_value", float("inf")) <= threshold)
    ]
    if not within_se:
        within_se = [best]

    # Pick simplest within the 1-SE band
    champion = min(within_se, key=lambda e: get_complexity(e.get("model_type", "")))

    # SE floor check
    continue_hpo, se_msg = se_floor_check(valid)

    result = {
        "name": champion.get("name"),
        "model_type": champion.get("model_type"),
        "params": champion.get("params", {}),
        "metric_name": champion.get("metric_name"),
        "metric_value": champion.get("metric_value"),
        "contract_hash": contract_hash,
        "seed": champion.get("seed"),
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "selection_method": "1se-parsimony",
        "within_1se_count": len(within_se),
        "total_experiments": len(valid),
        "se_floor": {"continue_hpo": continue_hpo, "detail": se_msg},
        "fold_scores": champion.get("fold_scores"),
        "reproducible": champion.get("seed") is not None,
    }
    return result


def build_monitoring_contract(champion_path):
    """Generate a monitoring contract from the champion."""
    with open(champion_path) as f:
        champion = json.load(f)

    return {
        "model_name": champion.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_metric": {
            "name": champion.get("metric_name"),
            "value": champion.get("metric_value"),
            "fold_scores": champion.get("fold_scores"),
        },
        "drift_checks": {
            "input_drift": {
                "method": "PSI",
                "threshold": 0.2,
                "check_frequency": "weekly",
            },
            "output_drift": {
                "method": "KS-test on score distribution",
                "threshold": 0.05,
                "check_frequency": "weekly",
            },
            "performance_decay": {
                "method": "compare production metric to baseline ± 2SE",
                "threshold": "2SE below baseline",
                "check_frequency": "weekly",
            },
        },
        "operational_checks": {
            "queue_size_drift": {
                "description": "Monitor if flagged volume drifts beyond review capacity (A6)",
                "check_frequency": "daily",
            },
            "action_rate": {
                "description": "Track what fraction of flagged items receive an action",
                "check_frequency": "weekly",
            },
        },
        "retrain_triggers": [
            "PSI > 0.2 on any top-5 feature",
            "Performance metric drops below baseline - 2SE for 2 consecutive weeks",
            "Action rate drops below 50% (model no longer driving useful decisions)",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    select_cmd = sub.add_parser("select")
    select_cmd.add_argument("--log-path", default=".eds/models/experiment_log.json")
    select_cmd.add_argument("--contract-path", default=".eds/models/validation_contract.json")
    select_cmd.add_argument("--out", default=".eds/models/champion.json")

    monitor_cmd = sub.add_parser("monitoring-contract")
    monitor_cmd.add_argument("--champion-path", default=".eds/models/champion.json")
    monitor_cmd.add_argument("--out", default=".eds/models/monitoring_contract.json")

    args = ap.parse_args()

    if args.cmd == "select":
        champion = select_champion(args.log_path, args.contract_path)
        if champion:
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            with open(args.out, "w") as f:
                json.dump(champion, f, indent=2)
            print(f"Champion: {champion['name']} ({champion['model_type']})")
            print(f"  {champion['metric_name']}={champion['metric_value']:.4f}")
            print(f"  SE floor: {champion['se_floor']['detail']}")
            print(f"  Written to {args.out}")
        else:
            print("No champion could be selected — no valid experiments found")

    elif args.cmd == "monitoring-contract":
        contract = build_monitoring_contract(args.champion_path)
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(contract, f, indent=2)
        print(f"Monitoring contract written to {args.out}")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
