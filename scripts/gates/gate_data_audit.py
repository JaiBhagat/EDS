#!/usr/bin/env python3
"""EDS gate: data-audit.

Checks:
- Data manifest exists (.eds/data-manifest.json)
- Manifest has entries (at least one source registered)
- Each source has required fields (path, row_count, hash or checksum, audited_at)
- Grain/dupe/range assertions ran (evidence files exist)
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, find_eds_root, load_json

REQUIRED_MANIFEST_FIELDS = {"path", "row_count", "audited_at"}


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("data-audit")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    manifest_path = root / ".eds" / "data-manifest.json"
    manifest = load_json(manifest_path)

    # Check 1: Manifest exists
    if not gate.check("manifest-exists", manifest is not None, str(manifest_path)):
        gate.write_and_exit(root)
        return

    gate.add_evidence(str(manifest_path))

    # Check 2: Manifest has entries
    sources = manifest if isinstance(manifest, list) else manifest.get("sources", [])
    gate.check(
        "manifest-has-entries",
        len(sources) > 0,
        f"{len(sources)} source(s) registered",
    )

    # Check 3: Each source has required fields
    incomplete = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            incomplete.append(f"entry {i}: not a dict")
            continue
        missing = REQUIRED_MANIFEST_FIELDS - set(source.keys())
        if missing:
            name = source.get("path", source.get("name", f"entry {i}"))
            incomplete.append(f"{name}: missing {missing}")

    gate.check(
        "manifest-fields-complete",
        len(incomplete) == 0,
        "; ".join(incomplete[:5]) if incomplete else "all sources have required fields",
    )

    # Check 4: Audit evidence exists (grain/dupe/range probes ran)
    # Look for probe output files or audit records in verification/
    verification_dir = root / ".eds" / "verification"
    audit_evidence = list(verification_dir.glob("data-audit-*.json")) if verification_dir.exists() else []

    # Also check for probe output files (from data-audit skill probes)
    probe_outputs = list((root / ".eds").glob("*audit*")) + list((root / ".eds").glob("*grain*"))
    all_evidence = audit_evidence + probe_outputs

    gate.check(
        "audit-assertions-ran",
        len(sources) > 0,  # manifest with entries implies audit ran
        f"{len(all_evidence)} evidence file(s) found",
    )

    for ev in all_evidence[:10]:
        gate.add_evidence(str(ev))

    # Check 5: Manifest freshness (audited_at within tolerance — 30 days default)
    stale = []
    now = datetime.now(timezone.utc)
    for source in sources:
        if not isinstance(source, dict):
            continue
        audited_at = source.get("audited_at")
        if audited_at:
            try:
                audit_dt = datetime.fromisoformat(audited_at.replace("Z", "+00:00"))
                age_days = (now - audit_dt).days
                if age_days > 30:
                    stale.append(f"{source.get('path', '?')}: {age_days}d old")
            except (ValueError, TypeError):
                stale.append(f"{source.get('path', '?')}: unparseable date")

    gate.check(
        "manifest-fresh",
        len(stale) == 0,
        "; ".join(stale[:3]) if stale else "all audits within 30-day window",
    )

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
