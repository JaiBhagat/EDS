#!/usr/bin/env python3
"""Regression tests for P3 improvements (A1–A4, B1, gate enforcement).

These tests lock down the fixes so they can't silently regress.
All tests use the synthetic fixture in tests/fixtures/.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add project root and scripts to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "mde" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "gates"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "lib"))

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# A1: test_brief_metric_parsing
# ---------------------------------------------------------------------------
class TestBriefMetricParsing:
    """A1 — read_brief_metric must handle real Brief formats."""

    def test_table_format(self) -> None:
        from validation_contract import read_brief_metric_from_text
        result = read_brief_metric_from_text(
            "| Primary metric | **Average Precision (AUPRC)** |"
        )
        assert result == "average_precision"

    def test_prose_format(self) -> None:
        from validation_contract import read_brief_metric_from_text
        result = read_brief_metric_from_text(
            "Primary metric: **Average Precision (AUPRC)** — more informative "
            "than ROC-AUC under severe class imbalance."
        )
        assert result == "average_precision"

    def test_unknown_metric_raises(self) -> None:
        from validation_contract import read_brief_metric_from_text
        with pytest.raises(ValueError, match="no known scorer"):
            read_brief_metric_from_text("| Primary metric | **Banana Score** |")

    def test_no_metric_returns_none(self) -> None:
        from validation_contract import read_brief_metric_from_text
        result = read_brief_metric_from_text("# Just some text, no metric here")
        assert result is None

    def test_roc_auc_variant(self) -> None:
        from validation_contract import read_brief_metric_from_text
        result = read_brief_metric_from_text(
            "| Primary metric | ROC-AUC |"
        )
        assert result == "roc_auc"

    def test_f1_variant(self) -> None:
        from validation_contract import read_brief_metric_from_text
        result = read_brief_metric_from_text(
            "Primary metric: F1 Score"
        )
        assert result == "f1"

    def test_fixture_brief(self) -> None:
        """The actual fixture Brief must parse correctly."""
        from validation_contract import read_brief_metric
        brief_path = FIXTURES / "eds_fixture" / ".eds" / "BRIEF.md"
        result = read_brief_metric(str(brief_path))
        assert result == "average_precision"


# ---------------------------------------------------------------------------
# A2: test_baseline_metric_resolution
# ---------------------------------------------------------------------------
class TestBaselineMetricResolution:
    """A2 — resolve_metric falls back to Brief when no contract exists."""

    def test_brief_fallback_no_contract(self, tmp_path: Path) -> None:
        """Brief present, no contract → resolves to Brief's metric."""
        # Create a Brief with AUPRC
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text("| Primary metric | **Average Precision (AUPRC)** |")

        # Ensure no contract exists
        models_dir = eds_dir / "models"
        models_dir.mkdir()
        contract_path = models_dir / "validation_contract.json"
        assert not contract_path.exists()

        # Use the baselines resolve_metric by importing with path setup
        sys.path.insert(0, str(PROJECT_ROOT / "skills" / "baseline-first" / "scripts"))
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            from baselines import resolve_metric
            # Reimport to get fresh module state
            import importlib
            import baselines
            importlib.reload(baselines)
            metric, source = baselines.resolve_metric(None)
            assert metric == "average_precision", f"Expected average_precision, got {metric}"
            assert source == "brief", f"Expected source=brief, got {source}"
        finally:
            os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# A4: test_notebook_assembly_fails_on_missing_code
# ---------------------------------------------------------------------------
class TestNotebookAssemblyMissingCode:
    """A4 — assembly must produce NotImplementedError cells when stage code is missing."""

    def test_missing_stage_code_produces_error_cell(self, tmp_path: Path) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "skills" / "notebook-assembly" / "scripts"))
        import importlib
        import assemble_notebook
        importlib.reload(assemble_notebook)

        eds_root = tmp_path / ".eds"
        eds_root.mkdir()

        stage = {"stage": "eda", "status": "done"}
        cells = assemble_notebook.build_stage_cells(stage, None, eds_root)

        # Should have a markdown header + warning markdown + error code cell
        assert len(cells) >= 3
        # Last cell should be code with NotImplementedError
        code_cell = cells[-1]
        assert code_cell["cell_type"] == "code"
        source_text = "".join(code_cell["source"])
        assert "NotImplementedError" in source_text

    def test_recorded_stage_code_produces_real_cells(self, tmp_path: Path) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "skills" / "notebook-assembly" / "scripts"))
        import importlib
        import assemble_notebook
        importlib.reload(assemble_notebook)

        eds_root = tmp_path / ".eds"
        stage_code_dir = eds_root / "stage_code"
        stage_code_dir.mkdir(parents=True)

        # Write a stage code record
        record = {
            "stage": "eda",
            "recorded_at": "2024-01-01T00:00:00Z",
            "cells": [
                {"kind": "code", "source": "import pandas as pd\ndf = pd.read_csv('data.csv')"},
                {"kind": "markdown", "source": "### Q: What's the target distribution?"},
            ]
        }
        (stage_code_dir / "eda.json").write_text(json.dumps(record))

        stage = {"stage": "eda", "status": "done"}
        cells = assemble_notebook.build_stage_cells(stage, None, eds_root)

        # Should have markdown header + 2 recorded cells
        assert len(cells) == 3
        # The code cell should contain the real code, not a stub
        code_cell = cells[1]
        assert code_cell["cell_type"] == "code"
        source_text = "".join(code_cell["source"])
        assert "pd.read_csv" in source_text
        assert "NotImplementedError" not in source_text


# ---------------------------------------------------------------------------
# B1: test_stage5_redundancy_equivalence
# ---------------------------------------------------------------------------
class TestStage5Redundancy:
    """B1 — vectorized stage_5_redundancy produces same results."""

    def test_equivalence_on_fixture(self) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "skills" / "fde" / "scripts" / "evaluators"))
        import importlib
        import funnel
        importlib.reload(funnel)

        rng = np.random.default_rng(42)
        n = 500
        df = pd.DataFrame({
            "a": rng.normal(size=n),
            "b": rng.normal(size=n),
            "c": None,
            "d": rng.normal(size=n),
            "e": rng.choice(["x", "y", "z"], n),
        })
        # c is a near-duplicate of a (r > 0.9)
        df["c"] = df["a"] * 1.0 + rng.normal(0, 0.1, n)

        candidates = ["a", "b", "c", "d", "e"]
        survivors, evictions = funnel.stage_5_redundancy(df, candidates)

        # a should survive, c should be evicted (redundant with a)
        assert "a" in survivors
        assert "c" not in survivors
        evicted_names = [e[0] for e in evictions]
        assert "c" in evicted_names
        # Non-numeric columns pass through
        assert "e" in survivors


# ---------------------------------------------------------------------------
# A4f: test_gate_blocks_unrecorded_stage
# ---------------------------------------------------------------------------
class TestGateBlocksUnrecordedStage:
    """A4f — gate exits non-zero when stage_code is missing."""

    def test_check_stage_code_fails_on_missing(self, tmp_path: Path) -> None:
        from gate_utils import GateResult, check_stage_code

        root = tmp_path
        (root / ".eds").mkdir()
        gate = GateResult("eda")

        result = check_stage_code(gate, root, "eda")
        assert result is False
        assert not gate.passed

    def test_check_stage_code_fails_on_empty_cells(self, tmp_path: Path) -> None:
        from gate_utils import GateResult, check_stage_code

        root = tmp_path
        stage_code_dir = root / ".eds" / "stage_code"
        stage_code_dir.mkdir(parents=True)
        (stage_code_dir / "eda.json").write_text(json.dumps({"stage": "eda", "cells": []}))

        gate = GateResult("eda")
        result = check_stage_code(gate, root, "eda")
        assert result is False

    def test_check_stage_code_passes_on_valid(self, tmp_path: Path) -> None:
        from gate_utils import GateResult, check_stage_code

        root = tmp_path
        stage_code_dir = root / ".eds" / "stage_code"
        stage_code_dir.mkdir(parents=True)
        record = {"stage": "eda", "cells": [{"kind": "code", "source": "x = 1"}]}
        (stage_code_dir / "eda.json").write_text(json.dumps(record))

        gate = GateResult("eda")
        result = check_stage_code(gate, root, "eda")
        assert result is True
        assert gate.passed
