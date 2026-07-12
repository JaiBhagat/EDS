"""Tests for P2 (state contract) and P3 (session lifecycle).

Covers: manifest, progress/handoff, plan transitions, eds-init.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "state"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


class TestManifest:
    def test_register_source(self, tmp_path):
        from state.manifest import register_source, load_manifest

        data = tmp_path / "orders.csv"
        df = pd.DataFrame({"id": range(100), "date": pd.date_range("2024-01-01", periods=100), "amt": np.random.randn(100)})
        df.to_csv(data, index=False)

        manifest_path = str(tmp_path / "manifest.json")
        entry = register_source(str(data), manifest_path)

        assert entry["row_count"] == 100
        assert entry["hash"] is not None
        assert "date" in str(entry.get("time_col", "")) or "date" in str(entry.get("columns", ""))

        manifest = load_manifest(manifest_path)
        assert len(manifest) == 1

    def test_diff_detects_rowcount_drift(self, tmp_path):
        from state.manifest import register_source, diff_manifest

        data = tmp_path / "data.csv"
        df = pd.DataFrame({"x": range(100)})
        df.to_csv(data, index=False)

        manifest_path = str(tmp_path / "manifest.json")
        register_source(str(data), manifest_path, rowcount_tolerance=0.05)

        # Now add 20% more rows
        df2 = pd.DataFrame({"x": range(120)})
        df2.to_csv(data, index=False)

        findings = diff_manifest(manifest_path)
        assert len(findings) > 0
        types = {f["type"] for f in findings}
        assert "rowcount_drift" in types or "content_changed" in types

    def test_diff_no_change(self, tmp_path):
        from state.manifest import register_source, diff_manifest

        data = tmp_path / "data.csv"
        pd.DataFrame({"x": range(50)}).to_csv(data, index=False)

        manifest_path = str(tmp_path / "manifest.json")
        register_source(str(data), manifest_path)

        findings = diff_manifest(manifest_path)
        assert len(findings) == 0

    def test_diff_detects_missing_file(self, tmp_path):
        from state.manifest import register_source, diff_manifest

        data = tmp_path / "temp.csv"
        pd.DataFrame({"x": [1]}).to_csv(data, index=False)

        manifest_path = str(tmp_path / "manifest.json")
        register_source(str(data), manifest_path)

        os.unlink(data)
        findings = diff_manifest(manifest_path)
        assert any(f["type"] == "missing" for f in findings)


class TestProgress:
    def test_write_and_read_handoff(self, tmp_path):
        from state.progress import write_handoff, read_latest_handoff

        path = str(tmp_path / "progress.md")
        write_handoff(path, "fde", completed=["audit", "eda"],
                      in_flight="fde round 3, candidate batch 2 pending",
                      next_action="continue round 3")

        handoff = read_latest_handoff(path)
        assert handoff is not None
        assert handoff["current_stage"] == "fde"
        assert handoff["in_flight"] == "fde round 3, candidate batch 2 pending"
        assert "audit" in handoff["completed"]

    def test_multiple_handoffs_reads_latest(self, tmp_path):
        from state.progress import write_handoff, read_latest_handoff

        path = str(tmp_path / "progress.md")
        write_handoff(path, "audit", next_action="start eda")
        write_handoff(path, "eda", next_action="start fde")

        handoff = read_latest_handoff(path)
        assert handoff["current_stage"] == "eda"


class TestPlan:
    def _make_brief(self, tmp_path):
        eds = tmp_path / ".eds"
        eds.mkdir()
        brief = eds / "BRIEF.md"
        brief.write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · pending · none\n"
            "- eda · eda-workflow · pending · none\n"
            "- fde · fde · pending · none\n"
            "- baseline · baseline-first · pending · none\n"
        )
        return str(brief)

    def test_get_status(self, tmp_path):
        from state.plan import get_status

        brief_path = self._make_brief(tmp_path)
        status = get_status(brief_path)
        assert status["done"] == 0
        assert status["total"] == 4
        assert status["next_pending"]["stage"] == "audit"

    def test_transition_to_in_progress(self, tmp_path):
        from state.plan import transition_stage, get_status

        brief_path = self._make_brief(tmp_path)
        result = transition_stage(brief_path, "audit", "in-progress")
        assert result["new_status"] == "in-progress"

        status = get_status(brief_path)
        assert status["current"]["stage"] == "audit"

    def test_transition_to_done_with_gate(self, tmp_path):
        from state.plan import transition_stage, get_status

        brief_path = self._make_brief(tmp_path)
        transition_stage(brief_path, "audit", "done",
                         gate_record="verification/data-audit-20260712.json")

        status = get_status(brief_path)
        assert status["done"] == 1
        assert status["next_pending"]["stage"] == "eda"

        # Verify gate-record is in the file
        text = open(brief_path).read()
        assert "verification/data-audit-20260712.json" in text

    def test_skip_with_reason(self, tmp_path):
        from state.plan import transition_stage

        brief_path = self._make_brief(tmp_path)
        result = transition_stage(brief_path, "eda", "skipped", reason="data too small for EDA")
        assert "data too small" in result["new_status"]

    def test_invalid_status_raises(self, tmp_path):
        from state.plan import transition_stage

        brief_path = self._make_brief(tmp_path)
        with pytest.raises(ValueError, match="Invalid status"):
            transition_stage(brief_path, "audit", "invalid-status")


class TestEdsInit:
    def test_no_eds_dir(self, tmp_path):
        from eds_init import run_init
        output = run_init(str(tmp_path))
        assert "no .eds/ found" in output

    def test_with_plan(self, tmp_path):
        from eds_init import run_init

        eds = tmp_path / ".eds"
        eds.mkdir()
        (eds / "BRIEF.md").write_text(
            "# Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · gate-record: x.json\n"
            "- eda · eda-workflow · pending · none\n"
        )
        output = run_init(str(tmp_path))
        assert "plan" in output.lower()
        assert "1/" in output  # 1/2 done
        assert "env: OK" in output
