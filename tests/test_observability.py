"""Tests for P6 — observability (activity log) and harness audit (/eds-audit).
"""
import json
import os
import sys
import subprocess

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from activity_log import append_entry, tail_log, grep_log

AUDIT_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "eds_audit.py")


class TestActivityLog:
    def test_append_creates_file(self, tmp_path):
        log = str(tmp_path / "activity.log")
        line = append_entry(log, "gate:discovery", "pass", "/path/to/record.json", "4 checks")
        assert os.path.exists(log)
        assert "gate:discovery" in line
        assert "pass" in line

    def test_append_is_append_only(self, tmp_path):
        log = str(tmp_path / "activity.log")
        append_entry(log, "probe:schema_grain", "ran", "/data/orders.csv")
        append_entry(log, "gate:data-audit", "pass", "/verification/x.json")

        with open(log) as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert "schema_grain" in lines[0]
        assert "data-audit" in lines[1]

    def test_grep_filters(self, tmp_path):
        log = str(tmp_path / "activity.log")
        append_entry(log, "gate:discovery", "pass")
        append_entry(log, "probe:missingness", "ran")
        append_entry(log, "gate:eda", "fail")

        # Capture grep output
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            grep_log(log, "gate")
        output = buf.getvalue()
        assert "discovery" in output
        assert "eda" in output
        assert "missingness" not in output


class TestEdsAudit:
    def _run_audit(self, project_dir):
        result = subprocess.run(
            [sys.executable, AUDIT_SCRIPT, str(project_dir)],
            capture_output=True, text=True,
        )
        return result.stdout + result.stderr, result.returncode

    def test_fails_without_eds_dir(self, tmp_path):
        output, code = self._run_audit(tmp_path)
        assert code == 1
        assert "No .eds/" in output

    def test_passes_healthy_project(self, tmp_path):
        eds = tmp_path / ".eds"
        eds.mkdir()

        # Brief with confirmed status and plan with gated done stage
        (eds / "BRIEF.md").write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · gate-record: verification/data-audit-20260710.json\n"
            "- eda · eda-workflow · pending\n"
        )

        # Verification directory with passing gate
        ver = eds / "verification"
        ver.mkdir()
        (ver / "data-audit-20260710.json").write_text(json.dumps({
            "gate": "data-audit", "result": "pass", "checks": []
        }))

        # Data manifest
        from datetime import datetime, timezone
        (eds / "data-manifest.json").write_text(json.dumps([
            {"path": "data/orders.csv", "row_count": 1000,
             "audited_at": datetime.now(timezone.utc).isoformat()}
        ]))

        # Debt ledger (clean)
        (eds / "debt-ledger.md").write_text("# EDS debt ledger\n\nClean.\n")

        output, code = self._run_audit(tmp_path)
        assert code == 0
        assert "PASS" in output

    def test_fails_on_ungated_done_stage(self, tmp_path):
        eds = tmp_path / ".eds"
        eds.mkdir()

        (eds / "BRIEF.md").write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · done · no gate ref\n"
        )

        output, code = self._run_audit(tmp_path)
        # Plan-gates is critical, so audit should fail
        assert "FAIL" in output
        assert "without gate-record" in output or "ungated" in output.lower() or "gate" in output.lower()

    def test_fails_on_stale_manifest(self, tmp_path):
        eds = tmp_path / ".eds"
        eds.mkdir()

        (eds / "BRIEF.md").write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · pending\n"
        )

        # Stale manifest (60 days old)
        (eds / "data-manifest.json").write_text(json.dumps([
            {"path": "data/old.csv", "row_count": 500,
             "audited_at": "2026-05-01T00:00:00+00:00"}
        ]))

        output, code = self._run_audit(tmp_path)
        assert "stale" in output.lower() or "old" in output.lower() or "FAIL" in output

    def test_fails_on_table_format_plan(self, tmp_path):
        """P1.3: A table-formatted Plan is unparseable by the bullet parser → FAIL."""
        eds = tmp_path / ".eds"
        eds.mkdir()

        (eds / "BRIEF.md").write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "| stage | status | gate |\n"
            "|---|---|---|\n"
            "| data-audit | done | gate:data-audit-20240101 |\n"
            "| eda | pending | |\n"
        )

        output, code = self._run_audit(tmp_path)
        assert "FAIL" in output
        assert "malformed" in output.lower() or "table format" in output.lower() or "unparseable" in output.lower()

    def test_detects_holdout_duplicate(self, tmp_path):
        eds = tmp_path / ".eds"
        eds.mkdir()

        (eds / "BRIEF.md").write_text(
            "# Problem Brief\n\n## Status\nconfirmed\n\n## Plan\n"
            "- audit · data-audit · pending\n"
        )

        # Holdout ledger with duplicate touches
        (eds / "holdout_ledger.json").write_text(json.dumps({
            "touches": [
                {"stage": "model", "timestamp": "2026-07-10", "score": 0.80},
                {"stage": "model", "timestamp": "2026-07-11", "score": 0.82},
            ]
        }))

        output, code = self._run_audit(tmp_path)
        assert "duplicate" in output.lower()


class TestGateActivityLogging:
    def test_gate_appends_to_activity_log(self, tmp_path):
        """Verify that running a gate writes to .eds/activity.log."""
        eds = tmp_path / ".eds"
        eds.mkdir()

        # Run the discovery gate (will fail, but should still log)
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..",
             "scripts", "gates", "gate_discovery.py"), str(tmp_path)],
            capture_output=True, text=True,
        )

        log_path = eds / "activity.log"
        assert log_path.exists()
        content = log_path.read_text()
        assert "gate:discovery" in content
        assert "fail" in content
