"""Tests for the verification gate runners (scripts/gates/).

Covers gate_utils infrastructure and individual gate scripts.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "gates"))
from gate_utils import GateResult, find_eds_root, load_json


class TestGateResult:
    def test_passes_when_all_checks_pass(self):
        g = GateResult("test-gate")
        g.check("check-1", True, "ok")
        g.check("check-2", True, "ok")
        assert g.passed
        assert len(g.failed_checks) == 0

    def test_fails_when_any_check_fails(self):
        g = GateResult("test-gate")
        g.check("check-1", True, "ok")
        g.check("check-2", False, "bad")
        assert not g.passed
        assert len(g.failed_checks) == 1

    def test_record_has_required_fields(self):
        g = GateResult("test-gate")
        g.check("c1", True)
        g.add_evidence("/path/to/file")
        record = g.to_record()
        assert record["gate"] == "test-gate"
        assert record["result"] == "pass"
        assert "timestamp" in record
        assert "duration_ms" in record
        assert len(record["checks"]) == 1
        assert record["evidence_paths"] == ["/path/to/file"]


class TestGateDiscovery:
    def test_fails_without_brief(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        result = _run_gate("gate_discovery", str(tmp_path))
        assert result["result"] == "fail"

    def test_fails_without_plan(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(_make_brief(plan=False, confirmed=True))
        result = _run_gate("gate_discovery", str(tmp_path))
        assert result["result"] == "fail"
        failed = {c["name"] for c in result["checks"] if not c["passed"]}
        assert "plan-present" in failed

    def test_fails_without_confirmed(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(_make_brief(plan=True, confirmed=False))
        result = _run_gate("gate_discovery", str(tmp_path))
        assert result["result"] == "fail"
        failed = {c["name"] for c in result["checks"] if not c["passed"]}
        assert "status-confirmed" in failed

    def test_passes_with_complete_brief(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        brief = eds_dir / "BRIEF.md"
        brief.write_text(_make_brief(plan=True, confirmed=True))
        result = _run_gate("gate_discovery", str(tmp_path))
        assert result["result"] == "pass"


class TestGateDataAudit:
    def test_fails_without_manifest(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        result = _run_gate("gate_data_audit", str(tmp_path))
        assert result["result"] == "fail"

    def test_passes_with_valid_manifest(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        from datetime import datetime, timezone
        manifest = [
            {"path": "data/orders.csv", "row_count": 1000,
             "audited_at": datetime.now(timezone.utc).isoformat()}
        ]
        (eds_dir / "data-manifest.json").write_text(json.dumps(manifest))
        # Stage code record required by gate enforcement (A4f)
        sc_dir = eds_dir / "stage_code"
        sc_dir.mkdir()
        (sc_dir / "data_audit.json").write_text(json.dumps(
            {"stage": "data_audit", "cells": [{"kind": "code", "source": "audit()"}]}
        ))
        result = _run_gate("gate_data_audit", str(tmp_path))
        assert result["result"] == "pass"


class TestGateReport:
    def test_fails_without_report(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        result = _run_gate("gate_report", str(tmp_path))
        assert result["result"] == "fail"

    def test_passes_with_traced_report(self, tmp_path):
        eds_dir = tmp_path / ".eds"
        eds_dir.mkdir()
        report = tmp_path / "final_report.md"
        report.write_text(
            "# Report\n\n"
            "- Churn rate is 12.3% (see `output/churn_rate.csv`)\n"
            "- Model AUC = 0.82 → `models/champion_eval.json`\n"
            "- Lift of 3.1x at top decile [fig 1]\n"
        )
        # Stage code record required by gate enforcement (A4f)
        sc_dir = eds_dir / "stage_code"
        sc_dir.mkdir()
        (sc_dir / "report.json").write_text(json.dumps(
            {"stage": "report", "cells": [{"kind": "code", "source": "report()"}]}
        ))
        result = _run_gate("gate_report", str(tmp_path))
        assert result["result"] == "pass"


# --- helpers ---

def _run_gate(gate_name: str, project_dir: str) -> dict:
    """Import and run a gate, capturing the result without sys.exit."""
    import importlib.util
    gate_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "gates", f"{gate_name}.py"
    )
    spec = importlib.util.spec_from_file_location(gate_name, gate_path)
    mod = importlib.util.module_from_spec(spec)

    # Monkey-patch write_and_exit to capture result instead of exiting
    captured = {}

    import types
    original_write_and_exit = GateResult.write_and_exit

    def mock_write_and_exit(self, eds_root):
        captured["record"] = self.to_record()
        # Still write the file
        verification_dir = eds_root / ".eds" / "verification"
        verification_dir.mkdir(parents=True, exist_ok=True)

    GateResult.write_and_exit = mock_write_and_exit
    try:
        spec.loader.exec_module(mod)
        mod.run(project_dir)
    finally:
        GateResult.write_and_exit = original_write_and_exit

    return captured.get("record", {"result": "error", "checks": []})


def _make_brief(plan: bool = True, confirmed: bool = True) -> str:
    status = "confirmed" if confirmed else "draft"
    sections = f"""# Problem Brief

## Status
{status}
version: 1

## Decision
Decide whether to intervene on high-risk customers.

## Stage 0 — Value & solution class
- Value estimate: ~$2M/yr
- Verdict: GO

## Confirmed problem statement
Predict customer churn at weekly cadence.

## Data inventory
| Source | Grain | Time coverage | Access | Status |
|---|---|---|---|---|
| orders | order_id | 2022-2024 | direct | have |

## Target & label strategy
Binary churn: no order in 90 days.

## Unit & grain
customer_id, weekly snapshot.

## Time semantics
Observation 90d, performance 90d.

## Task type
supervised · classification

## Operational constraints & consumption path
Batch weekly, top 500 reviewed by retention team.

## Success metric & baseline bar
Precision@500 >= 0.30, beating random baseline.

## Open questions & deferred items
None.
"""
    if plan:
        sections += """
## Plan
- audit · data-audit · pending
- eda · eda-workflow · pending
- fde · fde · pending
"""
    return sections
