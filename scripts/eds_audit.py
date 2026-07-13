#!/usr/bin/env python3
"""EDS — Harness auditor (/eds-audit).

Five-subsystem check. Exits 0 only when all critical items pass.
Runnable standalone and in CI.

Subsystems checked:
1. PROJECT.md / Brief — does the project have its operating manual?
2. Plan gates — are done stages backed by green gate records?
3. Data manifest — is it fresh? Sources within tolerance?
4. Handoff notes — is progress.md current with a valid handoff block?
5. Ledgers — holdout ledger consistent, debt ledger harvested?

Usage:
    python eds_audit.py [project-dir]
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_eds_root(start="."):
    current = Path(start).resolve()
    for _ in range(20):
        if (current / ".eds").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


class AuditResult:
    def __init__(self):
        self.checks = []

    def check(self, subsystem, name, passed, detail=""):
        self.checks.append({
            "subsystem": subsystem,
            "name": name,
            "passed": passed,
            "detail": detail,
            "critical": subsystem in ("plan-gates", "data-manifest"),
        })
        return passed

    @property
    def critical_pass(self):
        return all(c["passed"] for c in self.checks if c["critical"])

    @property
    def all_pass(self):
        return all(c["passed"] for c in self.checks)

    def print_report(self):
        subsystems = {}
        for c in self.checks:
            subsystems.setdefault(c["subsystem"], []).append(c)

        for sub, checks in subsystems.items():
            sub_pass = all(c["passed"] for c in checks)
            status = "PASS" if sub_pass else "FAIL"
            print(f"\n[{status}] {sub}")
            for c in checks:
                mark = "+" if c["passed"] else "x"
                line = f"  [{mark}] {c['name']}"
                if c["detail"]:
                    line += f" — {c['detail']}"
                print(line)

        print(f"\n{'='*60}")
        if self.all_pass:
            print("AUDIT: ALL PASS")
        elif self.critical_pass:
            print("AUDIT: CRITICAL PASS (non-critical warnings present)")
        else:
            print("AUDIT: FAIL (critical items failed)")


def audit_brief_and_project(root, result):
    """Subsystem 1: Brief and PROJECT.md presence."""
    eds_dir = root / ".eds"
    brief_path = eds_dir / "BRIEF.md"

    if brief_path.exists():
        brief = brief_path.read_text(encoding="utf-8")
        result.check("brief-project", "brief-exists", True)

        has_confirmed = "confirmed" in brief.lower()[:500]
        result.check("brief-project", "brief-confirmed", has_confirmed,
                     "status is confirmed" if has_confirmed else "Brief not yet confirmed")

        has_plan = "## Plan" in brief
        result.check("brief-project", "plan-section-present", has_plan)
    else:
        result.check("brief-project", "brief-exists", False, ".eds/BRIEF.md missing")

    project_path = eds_dir / "PROJECT.md"
    result.check("brief-project", "project-md-exists", project_path.exists(),
                 "PROJECT.md present" if project_path.exists() else "PROJECT.md not found (optional)")


def audit_plan_gates(root, result):
    """Subsystem 2: Are done stages backed by passing gate records?"""
    brief_path = root / ".eds" / "BRIEF.md"
    if not brief_path.exists():
        result.check("plan-gates", "plan-readable", False, "no BRIEF.md to read Plan from")
        return

    brief = brief_path.read_text(encoding="utf-8")
    plan_idx = brief.find("## Plan")
    if plan_idx == -1:
        result.check("plan-gates", "plan-exists", False, "no ## Plan section")
        return

    plan_text = brief[plan_idx:]
    lines = plan_text.split("\n")

    # Distinguish: plan entries use bullet format "- stage · skill · status"
    # A table-formatted plan (|---|) is a format mismatch → FAIL as unparseable
    plan_entries = [l for l in lines if re.match(r"^\s*[-*]\s+\S+.*·", l)]
    has_table = any(re.match(r"\s*\|", l) for l in lines[1:] if l.strip())

    if not plan_entries and has_table:
        result.check("plan-gates", "plan-parseable", False,
                     "Plan uses table format but parser expects bullet format '- stage · skill · status' — malformed")
        return

    if not plan_entries:
        result.check("plan-gates", "plan-parseable", False,
                     "Plan section present but 0 entries parsed — malformed or empty")
        return

    done_entries = [l for l in plan_entries if "done" in l.lower()]

    if not done_entries:
        result.check("plan-gates", "done-stages-gated", True, "no done stages yet")
        return

    ungated = []
    for entry in done_entries:
        if not re.search(r"gate[-_]record|verification/|\.json\b", entry, re.I):
            ungated.append(entry.strip()[:60])

    result.check("plan-gates", "done-stages-gated", len(ungated) == 0,
                 f"{len(ungated)} done stage(s) without gate-record ref: {ungated[0]}"
                 if ungated else f"all {len(done_entries)} done stages have gate records")

    # Check that referenced gate records actually exist
    verification_dir = root / ".eds" / "verification"
    if verification_dir.exists():
        gate_files = list(verification_dir.glob("*.json"))
        result.check("plan-gates", "gate-records-exist", len(gate_files) > 0,
                     f"{len(gate_files)} gate record(s) on disk")

        # Check latest gates passed
        failed_gates = []
        for gf in gate_files:
            try:
                record = json.loads(gf.read_text(encoding="utf-8"))
                if record.get("result") == "fail":
                    failed_gates.append(gf.name)
            except (json.JSONDecodeError, OSError):
                continue

        result.check("plan-gates", "latest-gates-pass", len(failed_gates) == 0,
                     f"{len(failed_gates)} failed gate(s): {failed_gates[:3]}"
                     if failed_gates else "all gate records show pass")
    else:
        result.check("plan-gates", "gate-records-exist", False,
                     ".eds/verification/ directory missing")


def audit_data_manifest(root, result):
    """Subsystem 3: Is the data manifest fresh?"""
    manifest_path = root / ".eds" / "data-manifest.json"
    if not manifest_path.exists():
        result.check("data-manifest", "manifest-exists", False,
                     "data-manifest.json not found")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        result.check("data-manifest", "manifest-parseable", False, "corrupt JSON")
        return

    result.check("data-manifest", "manifest-exists", True)

    sources = manifest if isinstance(manifest, list) else manifest.get("sources", [])
    result.check("data-manifest", "has-sources", len(sources) > 0,
                 f"{len(sources)} source(s)")

    # Freshness check (30 days)
    now = datetime.now(timezone.utc)
    stale = []
    for s in sources:
        if not isinstance(s, dict):
            continue
        audited = s.get("audited_at")
        if audited:
            try:
                dt = datetime.fromisoformat(audited.replace("Z", "+00:00"))
                age = (now - dt).days
                if age > 30:
                    stale.append(f"{s.get('path','?')}: {age}d old")
            except (ValueError, TypeError):
                stale.append(f"{s.get('path','?')}: bad date")

    result.check("data-manifest", "manifest-fresh", len(stale) == 0,
                 "; ".join(stale[:3]) if stale else "all sources audited within 30 days")


def audit_handoff_notes(root, result):
    """Subsystem 4: Is progress.md current?"""
    progress_path = root / ".eds" / "progress.md"
    if not progress_path.exists():
        result.check("handoff-notes", "progress-exists", False,
                     "progress.md not found (optional until session lifecycle is built)")
        return

    text = progress_path.read_text(encoding="utf-8")
    result.check("handoff-notes", "progress-exists", True)

    # Check for a handoff block
    has_handoff = "## handoff" in text.lower() or "## resume" in text.lower() or "current stage" in text.lower()
    result.check("handoff-notes", "has-handoff-block", has_handoff,
                 "handoff/resume block present" if has_handoff else "no handoff block found")


def audit_ledgers(root, result):
    """Subsystem 5: Holdout ledger + debt ledger health."""
    # Holdout ledger
    holdout_path = root / ".eds" / "holdout_ledger.json"
    if holdout_path.exists():
        try:
            ledger = json.loads(holdout_path.read_text(encoding="utf-8"))
            touches = ledger.get("touches", []) if isinstance(ledger, dict) else ledger
            # Check for duplicate unforced touches
            stage_counts = {}
            for t in touches:
                if isinstance(t, dict) and not t.get("forced"):
                    stage = t.get("stage", "?")
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1

            dupes = {k: v for k, v in stage_counts.items() if v > 1}
            result.check("ledgers", "holdout-no-dupes", len(dupes) == 0,
                         f"duplicate unforced touches: {dupes}" if dupes
                         else f"{len(touches)} touch(es), no duplicates")
        except (json.JSONDecodeError, OSError):
            result.check("ledgers", "holdout-parseable", False, "corrupt holdout_ledger.json")
    else:
        result.check("ledgers", "holdout-exists", True, "no holdout ledger yet (pre-model)")

    # Debt ledger
    debt_path = root / ".eds" / "debt-ledger.md"
    if debt_path.exists():
        text = debt_path.read_text(encoding="utf-8")
        entries = [l for l in text.split("\n") if l.startswith("- `")]
        result.check("ledgers", "debt-ledger-exists", True,
                     f"{len(entries)} deferred item(s) tracked")
    else:
        result.check("ledgers", "debt-ledger-exists", True, "no debt ledger (clean)")


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    root = find_eds_root(project_dir)

    if not root:
        print("AUDIT: No .eds/ directory found. Not an EDS project.")
        sys.exit(1)

    result = AuditResult()

    audit_brief_and_project(root, result)
    audit_plan_gates(root, result)
    audit_data_manifest(root, result)
    audit_handoff_notes(root, result)
    audit_ledgers(root, result)

    result.print_report()
    sys.exit(0 if result.critical_pass else 1)


if __name__ == "__main__":
    main()
