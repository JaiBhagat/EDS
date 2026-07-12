"""Tests for the harvest-debt.js Stop hook.

Covers the B2 bug: markers embedded inside string literals should not
be harvested. Only standalone comment markers at line start should be.
"""
import json
import os
import subprocess
import tempfile

import pytest

HARVEST_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "hooks", "scripts", "harvest-debt.js"
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with .eds/."""
    eds_dir = tmp_path / ".eds"
    eds_dir.mkdir()
    ledger = eds_dir / "debt-ledger.md"
    ledger.write_text("# EDS debt ledger\n\nHarvested.\n")
    return tmp_path


def run_harvest(project_dir: str) -> str:
    """Run harvest-debt.js and return the ledger content."""
    subprocess.run(
        ["node", HARVEST_SCRIPT],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    ledger_path = os.path.join(project_dir, ".eds", "debt-ledger.md")
    with open(ledger_path) as f:
        return f.read()


class TestHarvestDebt:
    def test_harvests_real_marker(self, project_dir):
        src = project_dir / "analysis.py"
        src.write_text("# eds: deferred — skipping cross-validation for speed\nprint(1)\n")

        ledger = run_harvest(str(project_dir))
        assert "skipping cross-validation for speed" in ledger

    def test_ignores_marker_in_string(self, project_dir):
        src = project_dir / "funnel.py"
        src.write_text(
            'raise RuntimeError("requires # eds: deferred — holdout re-use marker")\n'
        )

        ledger = run_harvest(str(project_dir))
        assert "holdout re-use" not in ledger

    def test_ignores_marker_in_docstring(self, project_dir):
        src = project_dir / "example.py"
        src.write_text(
            '"""Example: leave a # eds: deferred — reason marker."""\n'
        )

        ledger = run_harvest(str(project_dir))
        assert "reason marker" not in ledger

    def test_harvests_indented_marker(self, project_dir):
        src = project_dir / "code.py"
        src.write_text("    # eds: deferred — needs real DB connection\n")

        ledger = run_harvest(str(project_dir))
        assert "needs real DB connection" in ledger

    def test_deduplicates_existing_entries(self, project_dir):
        src = project_dir / "code.py"
        src.write_text("# eds: deferred — already harvested\n")

        # Harvest twice
        run_harvest(str(project_dir))
        ledger = run_harvest(str(project_dir))

        # Should appear only once
        assert ledger.count("already harvested") == 1

    def test_handles_em_dash_and_double_dash(self, project_dir):
        src1 = project_dir / "a.py"
        src1.write_text("# eds: deferred -- double dash reason\n")
        src2 = project_dir / "b.py"
        src2.write_text("# eds: deferred - single dash reason\n")

        ledger = run_harvest(str(project_dir))
        assert "double dash reason" in ledger
        assert "single dash reason" in ledger
