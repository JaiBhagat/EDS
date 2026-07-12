#!/usr/bin/env python3
"""EDS — Session initialization (H5: initialize before you analyze).

Runs at session start (via session-start hook or manually):
1. Environment check (imports for the stack the Plan needs)
2. Data-manifest diff (out-of-tolerance drift → re-audit)
3. State reconciliation (catalog↔journal, half-written round detection)
4. Plan status summary

Emits a compact status block for the model's context.

Usage:
    python eds_init.py [project-dir]
"""
import importlib
import json
import os
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


def check_environment():
    """Check that key DS packages are importable."""
    required = ["pandas", "numpy", "sklearn"]
    missing = []
    versions = {}
    for pkg in required:
        try:
            mod = importlib.import_module(pkg)
            versions[pkg] = getattr(mod, "__version__", "?")
        except ImportError:
            missing.append(pkg)
    return missing, versions


def check_manifest_drift(eds_root):
    """Diff the data manifest against current files."""
    manifest_path = eds_root / ".eds" / "data-manifest.json"
    if not manifest_path.exists():
        return None, []

    try:
        sys.path.insert(0, str(eds_root / "scripts" / "state"))
        from manifest import diff_manifest
        findings = diff_manifest(str(manifest_path))
        return manifest_path, findings
    except ImportError:
        return manifest_path, []


def check_state_reconciliation(eds_root):
    """Check for catalog↔journal consistency and half-written rounds."""
    issues = []

    # FDE catalog vs journal
    catalog_path = eds_root / ".eds" / "features" / "feature_catalog.json"
    journal_path = eds_root / ".eds" / "features" / "feature_journal.json"

    if catalog_path.exists() and journal_path.exists():
        try:
            catalog = json.loads(catalog_path.read_text())
            journal = json.loads(journal_path.read_text())
            catalog_names = {e.get("name") for e in catalog if isinstance(e, dict)}
            journal_names = set()
            rounds = journal if isinstance(journal, list) else journal.get("rounds", [])
            for r in rounds:
                if isinstance(r, dict):
                    for feat in r.get("accepted", []):
                        if isinstance(feat, str):
                            journal_names.add(feat)
                        elif isinstance(feat, dict):
                            journal_names.add(feat.get("name", ""))

            orphans = journal_names - catalog_names
            if orphans:
                issues.append(f"journal refs {len(orphans)} feature(s) not in catalog: {list(orphans)[:3]}")
        except (json.JSONDecodeError, OSError):
            pass

    # Half-written experiment rounds
    log_path = eds_root / ".eds" / "models" / "experiment_log.json"
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text())
            experiments = log.get("experiments", [])
            if experiments:
                last = experiments[-1]
                if last.get("metric_value") is None:
                    issues.append(f"last experiment '{last.get('name')}' has no metric — incomplete run?")
        except (json.JSONDecodeError, OSError):
            pass

    return issues


def get_plan_status(eds_root):
    """Extract plan status for the summary line."""
    brief_path = eds_root / ".eds" / "BRIEF.md"
    if not brief_path.exists():
        return None

    text = brief_path.read_text(encoding="utf-8")
    plan_idx = text.find("## Plan")
    if plan_idx == -1:
        return None

    import re
    plan_text = text[plan_idx:]
    entries = [l for l in plan_text.split("\n") if re.match(r"^\s*[-*]\s+\S", l)]
    if not entries:
        return None

    done = sum(1 for e in entries if "done" in e.lower() and "done" in e.split("·")[2].lower() if len(e.split("·")) > 2)
    total = len(entries)

    # Count done more robustly
    done = 0
    next_stage = None
    for e in entries:
        parts = e.split("·")
        if len(parts) >= 3:
            status = parts[2].strip().lower()
            if "done" in status:
                done += 1
            elif "skipped" in status:
                total -= 1
            elif not next_stage and "pending" in status:
                stage_name = parts[0].strip().lstrip("-* ").strip()
                next_stage = stage_name

    return {"done": done, "total": total, "next": next_stage}


def get_resume_point(eds_root):
    """Read the latest handoff note for resume info."""
    progress_path = eds_root / ".eds" / "progress.md"
    if not progress_path.exists():
        return None
    try:
        sys.path.insert(0, str(eds_root / "scripts" / "state"))
        from progress import read_latest_handoff
        return read_latest_handoff(str(progress_path))
    except ImportError:
        return None


def run_init(project_dir="."):
    """Run full initialization and return the status block."""
    root = find_eds_root(project_dir)
    if not root:
        return "EDS · no .eds/ found — run /discover to start"

    lines = []

    # Mode (from session-start.js already, but we add plan status)
    plan = get_plan_status(root)
    if plan:
        plan_line = f"EDS · plan {plan['done']}/{plan['total']} done"
        if plan["next"]:
            plan_line += f" · next: {plan['next']}"
        lines.append(plan_line)
    else:
        lines.append("EDS · no Plan yet — run /discover")

    # Data manifest diff
    manifest_path, drift_findings = check_manifest_drift(root)
    if manifest_path:
        if drift_findings:
            errors = [f for f in drift_findings if f["severity"] in ("error", "warning")]
            if errors:
                lines.append(f"data: {len(errors)} source(s) DRIFTED since audit — re-audit required")
                for f in errors[:2]:
                    lines.append(f"  {f['path']}: {f['detail']}")
            else:
                lines.append(f"data: {len(drift_findings)} change(s) within tolerance")
        else:
            lines.append("data: all sources match manifest")
    else:
        lines.append("data: no manifest yet")

    # Environment
    missing, versions = check_environment()
    if missing:
        lines.append(f"env: MISSING {missing}")
    else:
        pkg_str = ", ".join(f"{k} {v}" for k, v in versions.items())
        lines.append(f"env: OK ({pkg_str})")

    # State reconciliation
    issues = check_state_reconciliation(root)
    if issues:
        lines.append(f"state: {len(issues)} issue(s)")
        for i in issues[:2]:
            lines.append(f"  {i}")

    # Resume point
    resume = get_resume_point(root)
    if resume and resume.get("in_flight"):
        lines.append(f"resume: {resume['in_flight']}")

    return "\n".join(lines)


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output = run_init(project_dir)
    print(output)


if __name__ == "__main__":
    main()
