"""Regression tests for the FDE funnel (skills/fde/scripts/evaluators/funnel.py).

Covers the B1 dtype bug (pandas 3.x str dtype) and the core staged
evaluation pipeline.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "fde", "scripts", "evaluators"))
import funnel


@pytest.fixture
def demo_df():
    rng = np.random.default_rng(7)
    n = 400
    df = pd.DataFrame({
        "signal_good": rng.normal(size=n),
        "leak_perfect": None,
        "near_constant": np.where(rng.random(n) < 0.995, 0, 1),
        "high_card_str": [f"id_{i}" for i in range(n)],
        "mostly_missing": [np.nan] * (n - 5) + list(rng.normal(size=5)),
        "event_time": pd.date_range("2024-01-01", periods=n, freq="D"),
    })
    y = (df["signal_good"] + rng.normal(scale=0.5, size=n) > 0).astype(int)
    df["target"] = y
    df["leak_perfect"] = y
    df["dup_of_signal_good"] = df["signal_good"]
    return df


CANDIDATES = ["signal_good", "leak_perfect", "near_constant", "high_card_str",
               "mostly_missing", "dup_of_signal_good"]


class TestStage0LeakageScan:
    def test_catches_perfect_correlation(self, demo_df):
        survivors, evictions = funnel.stage_0_leakage_scan(demo_df, "target", CANDIDATES)
        assert "leak_perfect" not in survivors
        evicted_names = {e[0] for e in evictions}
        assert "leak_perfect" in evicted_names

    def test_keeps_real_signal(self, demo_df):
        survivors, _ = funnel.stage_0_leakage_scan(demo_df, "target", CANDIDATES)
        assert "signal_good" in survivors


class TestStage1DegenerateFilter:
    def test_catches_near_constant(self, demo_df):
        survivors, _ = funnel.stage_1_degenerate_filter(demo_df, CANDIDATES)
        assert "near_constant" not in survivors

    def test_catches_duplicates(self, demo_df):
        survivors, _ = funnel.stage_1_degenerate_filter(demo_df, CANDIDATES)
        assert not ("dup_of_signal_good" in survivors and "signal_good" in survivors)


class TestStage2Missingness:
    def test_catches_mostly_missing(self, demo_df):
        survivors, _ = funnel.stage_2_missingness(demo_df, CANDIDATES)
        assert "mostly_missing" not in survivors


class TestStage3Cardinality:
    def test_catches_high_cardinality_string(self, demo_df):
        """B1 regression: under pandas 3.x the default string dtype is 'str',
        not 'object'.  This test catches the original bug where
        `df[col].dtype == object` missed string columns."""
        survivors, evictions = funnel.stage_3_cardinality(demo_df, CANDIDATES)
        assert "high_card_str" not in survivors, (
            "stage 3 should catch the high-cardinality string column — "
            "this is the B1 dtype bug regression test"
        )

    def test_catches_string_dtype_explicitly(self):
        """Explicit test with StringDtype to verify pandas 3.x compatibility."""
        df = pd.DataFrame({
            "str_col": pd.array([f"cat_{i}" for i in range(200)], dtype="string"),
            "num_col": range(200),
        })
        survivors, evictions = funnel.stage_3_cardinality(df, ["str_col", "num_col"])
        assert "str_col" not in survivors
        assert "num_col" in survivors


class TestStage5Redundancy:
    def test_removes_one_of_redundant_pair(self, demo_df):
        candidates = ["signal_good", "dup_of_signal_good"]
        survivors, _ = funnel.stage_5_redundancy(demo_df, candidates)
        assert len(survivors) == 1


class TestStage7Stability:
    def test_catches_unstable_feature(self, demo_df):
        rng = np.random.default_rng(42)
        n = len(demo_df)
        # First half: perfect signal, second half: pure noise — extreme drift
        demo_df["unstable"] = np.where(
            np.arange(n) < n // 2,
            demo_df["target"].astype(float) + rng.normal(scale=0.1, size=n),
            rng.normal(size=n),
        )
        survivors, _ = funnel.stage_7_stability(
            demo_df, "target", ["signal_good", "unstable"],
            time_col="event_time", n_slices=3,
        )
        assert "unstable" not in survivors
        assert "signal_good" in survivors


class TestStage10Confirmation:
    def test_single_touch_guard(self, demo_df, tmp_path):
        touch_log = str(tmp_path / "touch.json")
        split = len(demo_df) // 2
        df_train, df_holdout = demo_df.iloc[:split], demo_df.iloc[split:]

        score = funnel.stage_10_confirmation(
            df_train, df_holdout, "target", ["signal_good"],
            touch_log_path=touch_log,
        )
        assert 0.0 <= score <= 1.0

        with pytest.raises(RuntimeError, match="already touched"):
            funnel.stage_10_confirmation(
                df_train, df_holdout, "target", ["signal_good"],
                touch_log_path=touch_log,
            )


class TestRunHardKillStages:
    def test_end_to_end(self, demo_df):
        survivors, trail = funnel.run_hard_kill_stages(demo_df, "target", CANDIDATES)
        assert "leak_perfect" not in survivors
        assert "near_constant" not in survivors
        assert "high_card_str" not in survivors
        assert "mostly_missing" not in survivors
        assert "signal_good" in survivors
        assert "input" in trail
        assert "stage_0" in trail


class TestIsCategoricalLike:
    def test_object_dtype(self):
        s = pd.Series(["a", "b", "c"], dtype="object")
        assert funnel._is_categorical_like(s)

    def test_string_dtype(self):
        s = pd.Series(["a", "b", "c"], dtype="string")
        assert funnel._is_categorical_like(s)

    def test_categorical_dtype(self):
        s = pd.Series(pd.Categorical(["a", "b", "c"]))
        assert funnel._is_categorical_like(s)

    def test_numeric_dtype(self):
        s = pd.Series([1, 2, 3])
        assert not funnel._is_categorical_like(s)
