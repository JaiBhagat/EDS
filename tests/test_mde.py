"""Tests for the MDE (Model Discovery Engine) scripts.

Covers: validation contract, experiment log, holdout ledger,
candidate table, calibration, and champion selection.
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "mde", "scripts"))


class TestValidationContract:
    def test_create_classification_contract(self, tmp_path):
        import pandas as pd
        from validation_contract import create_contract, compute_hash

        df = pd.DataFrame({
            "feat1": np.random.randn(100),
            "feat2": np.random.randn(100),
            "target": np.random.choice([0, 1], 100),
            "date": pd.date_range("2024-01-01", periods=100),
        })
        contract = create_contract(df, "target", time_col="date")
        assert contract["task_type"] == "classification"
        assert contract["metric"] == "roc_auc"
        assert contract["split_strategy"] == "temporal"
        assert contract["hash"] is not None
        assert len(contract["hash"]) == 16

    def test_create_regression_contract(self, tmp_path):
        import pandas as pd
        from validation_contract import create_contract

        df = pd.DataFrame({
            "feat1": np.random.randn(100),
            "target": np.random.randn(100),
        })
        contract = create_contract(df, "target")
        assert contract["task_type"] == "regression"
        assert contract["metric"] == "neg_rmse"
        assert contract["split_strategy"] == "random"

    def test_verify_intact_contract(self, tmp_path):
        import pandas as pd
        from validation_contract import create_contract, verify_contract

        df = pd.DataFrame({"f": [1, 2, 3], "t": [0, 1, 0]})
        contract = create_contract(df, "t")
        path = tmp_path / "contract.json"
        path.write_text(json.dumps(contract))

        ok, msg = verify_contract(str(path))
        assert ok

    def test_verify_tampered_contract(self, tmp_path):
        import pandas as pd
        from validation_contract import create_contract, verify_contract

        df = pd.DataFrame({"f": [1, 2, 3], "t": [0, 1, 0]})
        contract = create_contract(df, "t")
        contract["metric"] = "accuracy"  # tamper
        path = tmp_path / "contract.json"
        path.write_text(json.dumps(contract))

        ok, msg = verify_contract(str(path))
        assert not ok
        assert "mismatch" in msg.lower()

    def test_entity_aware_split(self, tmp_path):
        import pandas as pd
        from validation_contract import create_contract

        df = pd.DataFrame({
            "f": range(100), "t": [0, 1] * 50,
            "date": pd.date_range("2024-01-01", periods=100),
            "user_id": list(range(50)) * 2,
        })
        contract = create_contract(df, "t", time_col="date", entity_col="user_id")
        assert contract["split_strategy"] == "temporal-entity-aware"


class TestExperimentLog:
    def test_log_and_retrieve(self, tmp_path):
        from experiment_log import log_experiment, get_champion, load_log

        log_path = str(tmp_path / "log.json")

        log_experiment(log_path, "baseline", "LogisticRegression",
                       {}, "roc_auc", 0.72, "abc123", seed=42)
        log_experiment(log_path, "gbm-tuned", "GBM",
                       {"n_estimators": 200}, "roc_auc", 0.78, "abc123", seed=42)

        log = load_log(log_path)
        assert len(log["experiments"]) == 2

        champion = get_champion(log_path)
        assert champion["name"] == "gbm-tuned"
        assert champion["metric_value"] == 0.78

    def test_empty_log(self, tmp_path):
        from experiment_log import get_champion

        log_path = str(tmp_path / "empty.json")
        assert get_champion(log_path) is None


class TestHoldoutLedger:
    def test_single_touch_allowed(self, tmp_path):
        from holdout_ledger import record_touch, load_ledger

        path = str(tmp_path / "ledger.json")
        touch = record_touch(path, "model", 0.81)
        assert touch["stage"] == "model"
        assert touch["score"] == 0.81

    def test_second_touch_refused(self, tmp_path):
        from holdout_ledger import record_touch

        path = str(tmp_path / "ledger.json")
        record_touch(path, "model", 0.81)

        with pytest.raises(RuntimeError, match="already touched"):
            record_touch(path, "model", 0.82)

    def test_force_allows_second_touch(self, tmp_path):
        from holdout_ledger import record_touch

        path = str(tmp_path / "ledger.json")
        record_touch(path, "model", 0.81)
        touch = record_touch(path, "model", 0.82, force=True)
        assert touch["forced"]

    def test_different_stages_allowed(self, tmp_path):
        from holdout_ledger import record_touch, check_ledger

        path = str(tmp_path / "ledger.json")
        record_touch(path, "fde-confirmation", 0.75)
        record_touch(path, "model", 0.81)

        issues = check_ledger(path)
        assert len(issues) == 0


class TestCandidateTable:
    def test_init_classification(self, tmp_path):
        from candidate_table import init_table

        path = str(tmp_path / "table.json")
        table = init_table("classification", path)
        assert len(table["candidates"]) == 3
        assert table["candidates"][0]["name"] == "majority-class"

    def test_add_candidate_requires_rationale(self, tmp_path):
        from candidate_table import init_table, add_candidate

        path = str(tmp_path / "table.json")
        init_table("classification", path)
        entry = add_candidate(path, "RF-tuned", "RandomForest",
                              "High-variance errors in new-customer segment")
        assert entry["rationale"].startswith("High-variance")

    def test_mark_candidate(self, tmp_path):
        from candidate_table import init_table, mark_candidate

        path = str(tmp_path / "table.json")
        init_table("classification", path)
        mark_candidate(path, "majority-class", "evaluated", metric_value=0.50)

        with open(path) as f:
            table = json.load(f)
        entry = next(c for c in table["candidates"] if c["name"] == "majority-class")
        assert entry["status"] == "evaluated"
        assert entry["metric_value"] == 0.50


class TestCalibration:
    def test_well_calibrated_model(self):
        from calibration import calibration_check

        np.random.seed(42)
        n = 2000
        # Generate truly calibrated probabilities: uniform probs, then sample labels
        y_prob = np.random.uniform(0.05, 0.95, n)
        y_true = (np.random.uniform(0, 1, n) < y_prob).astype(int)

        report = calibration_check(y_true, y_prob)
        assert report["ece"] < 0.05
        assert "calibrat" in report["verdict"].lower()

    def test_miscalibrated_model(self):
        from calibration import calibration_check

        np.random.seed(42)
        y_true = np.random.choice([0, 1], 1000, p=[0.5, 0.5])
        # Miscalibrated: all predictions squeezed near 0.5
        y_prob = np.clip(0.45 + np.random.normal(0, 0.05, 1000), 0, 1)

        report = calibration_check(y_true, y_prob)
        assert report["ece"] > 0.05


class TestChampionSelection:
    def test_pareto_selects_simplest_on_front(self):
        from champion_selection import pareto_front

        experiments = [
            {"name": "logistic", "model_type": "LogisticRegression", "metric_value": 0.75},
            {"name": "gbm", "model_type": "GradientBoostingClassifier", "metric_value": 0.78},
            {"name": "mlp", "model_type": "MLPClassifier", "metric_value": 0.77},
        ]
        front = pareto_front(experiments)
        # GBM has best metric, logistic has best simplicity — both on front
        front_names = {e["name"] for e in front}
        assert "gbm" in front_names
        assert "logistic" in front_names

    def test_se_floor_stops_when_gap_small(self):
        from champion_selection import se_floor_check

        experiments = [
            {"name": "a", "metric_value": 0.801, "fold_scores": [0.79, 0.80, 0.81, 0.80, 0.81]},
            {"name": "b", "metric_value": 0.800, "fold_scores": [0.78, 0.80, 0.82, 0.79, 0.81]},
        ]
        should_continue, msg = se_floor_check(experiments)
        assert not should_continue  # gap too small relative to SE

    def test_select_champion_end_to_end(self, tmp_path):
        from experiment_log import log_experiment
        from champion_selection import select_champion
        import pandas as pd
        from validation_contract import create_contract

        # Create contract
        df = pd.DataFrame({"f": range(100), "t": np.random.choice([0, 1], 100)})
        contract = create_contract(df, "t")
        contract_path = str(tmp_path / "contract.json")
        with open(contract_path, "w") as f:
            json.dump(contract, f)

        # Log experiments
        log_path = str(tmp_path / "log.json")
        log_experiment(log_path, "baseline", "LogisticRegression",
                       {}, "roc_auc", 0.72, contract["hash"], seed=42)
        log_experiment(log_path, "gbm", "GradientBoostingClassifier",
                       {"n_estimators": 100}, "roc_auc", 0.78, contract["hash"], seed=42)

        champion = select_champion(log_path, contract_path)
        assert champion is not None
        # 1-SE rule: GBM (0.78) is the best. LogisticRegression (0.72)
        # is well outside 1 SE, so GBM wins.
        assert champion["name"] == "gbm"
        assert champion["contract_hash"] == contract["hash"]

    def test_monitoring_contract_generation(self, tmp_path):
        from champion_selection import build_monitoring_contract

        champion = {
            "name": "gbm-tuned",
            "metric_name": "roc_auc",
            "metric_value": 0.82,
            "fold_scores": [0.80, 0.81, 0.83, 0.82, 0.84],
        }
        champion_path = str(tmp_path / "champion.json")
        with open(champion_path, "w") as f:
            json.dump(champion, f)

        contract = build_monitoring_contract(champion_path)
        assert contract["model_name"] == "gbm-tuned"
        assert "drift_checks" in contract
        assert "retrain_triggers" in contract
        assert len(contract["retrain_triggers"]) >= 2
