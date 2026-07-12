"""Shared utilities for EDS verification gates.

Every gate:
1. Runs checks against .eds/ artifacts
2. Writes a structured JSON record to .eds/verification/
3. Exits 0 on pass, 1 on fail

The verification record schema:
{
  "gate": "<stage-name>",
  "timestamp": "ISO-8601",
  "result": "pass" | "fail",
  "checks": [{"name": str, "passed": bool, "detail": str}],
  "evidence_paths": [str],
  "duration_ms": int
}
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def find_eds_root(start: str = ".") -> Path | None:
    """Walk up from start to find .eds/ directory."""
    current = Path(start).resolve()
    for _ in range(20):
        if (current / ".eds").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def load_brief(eds_root: Path) -> str | None:
    """Load BRIEF.md content, or None if missing."""
    brief_path = eds_root / ".eds" / "BRIEF.md"
    if brief_path.exists():
        return brief_path.read_text(encoding="utf-8")
    return None


def load_json(path: Path) -> dict | list | None:
    """Load a JSON file, return None on missing/invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def check_stage_code(result: "GateResult", eds_root: Path, stage_name: str) -> bool:
    """Assert the stage recorded its executable code. Reproducibility (axiom 5)
    is a never-cut item: a stage whose code was never captured cannot be rerun
    or assembled, regardless of how good its findings were."""
    path = eds_root / ".eds" / "stage_code" / f"{stage_name}.json"
    recorded = load_json(path)
    ok = bool(recorded and recorded.get("cells"))
    result.check(
        "stage_code_recorded", ok,
        f"{path} present with non-empty cells" if ok
        else f"missing or empty — run `stage_code.py record --stage {stage_name}`",
    )
    if ok:
        result.add_evidence(str(path))
    return ok


class GateResult:
    """Accumulates check results for a single gate run."""

    def __init__(self, gate_name: str):
        self.gate_name = gate_name
        self.checks: list[dict] = []
        self.evidence_paths: list[str] = []
        self._start = time.monotonic()

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        """Record a single check. Returns passed for chaining."""
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        return passed

    def add_evidence(self, path: str):
        """Record an evidence artifact path."""
        self.evidence_paths.append(path)

    @property
    def passed(self) -> bool:
        return all(c["passed"] for c in self.checks)

    @property
    def failed_checks(self) -> list[dict]:
        return [c for c in self.checks if not c["passed"]]

    def to_record(self) -> dict:
        """Build the verification record."""
        return {
            "gate": self.gate_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": "pass" if self.passed else "fail",
            "checks": self.checks,
            "evidence_paths": self.evidence_paths,
            "duration_ms": int((time.monotonic() - self._start) * 1000),
        }

    def write_and_exit(self, eds_root: Path):
        """Write verification record and exit with appropriate code."""
        verification_dir = eds_root / ".eds" / "verification"
        verification_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        record_path = verification_dir / f"{self.gate_name}-{ts}.json"
        record = self.to_record()
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

        # Append to activity log (H7)
        activity_log = eds_root / ".eds" / "activity.log"
        try:
            log_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            result_str = "pass" if self.passed else "fail"
            log_line = f"{log_ts} | gate:{self.gate_name} | {result_str} | {record_path} | {len(self.checks)} checks\n"
            with open(activity_log, "a", encoding="utf-8") as f:
                f.write(log_line)
        except OSError:
            pass  # activity log is best-effort

        # Print summary
        status = "PASS" if self.passed else "FAIL"
        print(f"[gate:{self.gate_name}] {status}")
        for c in self.checks:
            mark = "+" if c["passed"] else "x"
            line = f"  [{mark}] {c['name']}"
            if c["detail"]:
                line += f" — {c['detail']}"
            print(line)

        if not self.passed:
            print(f"\nGate record: {record_path}")
            sys.exit(1)
        else:
            print(f"\nGate record: {record_path}")
            sys.exit(0)
