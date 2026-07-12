#!/usr/bin/env python3
"""EDS gate: fde (Feature Discovery Engine).

Checks:
- Funnel trail complete for selected feature set
- Feature catalog and journal reconcile (no orphans in either direction)
- Holdout ledger consistent (no double-touches)
- Funnel self-test passes in this environment
"""
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, check_stage_code, find_eds_root, load_json


def load_funnel_module(eds_root: Path):
    """Dynamically load funnel.py from the plugin."""
    # Try relative to this script (plugin install)
    candidates = [
        Path(__file__).parent.parent.parent / "skills" / "fde" / "scripts" / "evaluators" / "funnel.py",
        eds_root / "skills" / "fde" / "scripts" / "evaluators" / "funnel.py",
    ]
    for funnel_path in candidates:
        if funnel_path.exists():
            spec = importlib.util.spec_from_file_location("funnel", funnel_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("fde")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    features_dir = root / ".eds" / "features"

    # Check 1: Feature catalog exists and has entries
    catalog_path = features_dir / "feature_catalog.json"
    catalog = load_json(catalog_path)
    if not gate.check(
        "catalog-exists",
        catalog is not None,
        str(catalog_path),
    ):
        gate.write_and_exit(root)
        return

    gate.add_evidence(str(catalog_path))

    entries = catalog if isinstance(catalog, list) else catalog.get("features", [])
    gate.check("catalog-has-entries", len(entries) > 0, f"{len(entries)} feature(s)")

    # Check 2: Journal exists and reconciles with catalog
    journal_path = features_dir / "feature_journal.json"
    journal = load_json(journal_path)
    if journal is not None:
        gate.add_evidence(str(journal_path))
        journal_entries = journal if isinstance(journal, list) else journal.get("rounds", [])

        # Extract feature names from catalog
        catalog_names = set()
        for entry in entries:
            if isinstance(entry, dict):
                catalog_names.add(entry.get("name", entry.get("feature", "")))

        # Extract feature names from journal (accepted features)
        journal_names = set()
        for round_entry in journal_entries:
            if isinstance(round_entry, dict):
                for feat in round_entry.get("accepted", []):
                    if isinstance(feat, str):
                        journal_names.add(feat)
                    elif isinstance(feat, dict):
                        journal_names.add(feat.get("name", ""))

        # Check for orphans
        in_catalog_not_journal = catalog_names - journal_names if journal_names else set()
        in_journal_not_catalog = journal_names - catalog_names if catalog_names else set()

        orphan_detail = []
        if in_catalog_not_journal:
            orphan_detail.append(f"in catalog not journal: {list(in_catalog_not_journal)[:3]}")
        if in_journal_not_catalog:
            orphan_detail.append(f"in journal not catalog: {list(in_journal_not_catalog)[:3]}")

        gate.check(
            "catalog-journal-reconcile",
            len(in_journal_not_catalog) == 0,  # journal refs must exist in catalog
            "; ".join(orphan_detail) if orphan_detail else "catalog and journal reconciled",
        )
    else:
        gate.check("catalog-journal-reconcile", False, "feature_journal.json missing")

    # Check 3: Funnel trail complete for selected set
    # Selected features should have a funnel trail showing which stages they passed
    selected = [e for e in entries if isinstance(e, dict) and e.get("status") == "selected"]
    trail_missing = []
    for feat in selected:
        name = feat.get("name", feat.get("feature", ""))
        if not feat.get("funnel_trail") and not feat.get("stages_passed"):
            trail_missing.append(name)

    gate.check(
        "funnel-trail-complete",
        len(trail_missing) == 0,
        f"{len(trail_missing)} selected features lack funnel trail: {trail_missing[:3]}"
        if trail_missing
        else f"all {len(selected)} selected features have funnel trails",
    )

    # Check 4: Holdout ledger consistency
    ledger_path = root / ".eds" / "holdout_ledger.json"
    ledger = load_json(ledger_path)
    if ledger is not None:
        gate.add_evidence(str(ledger_path))
        touches = ledger if isinstance(ledger, list) else ledger.get("touches", [])
        # Check for duplicate touches (same holdout touched more than once per stage)
        seen = set()
        dupes = []
        for touch in touches:
            if isinstance(touch, dict):
                key = (touch.get("stage", ""), touch.get("holdout_id", ""))
                if key in seen:
                    dupes.append(key)
                seen.add(key)
        gate.check(
            "holdout-ledger-consistent",
            len(dupes) == 0,
            f"{len(dupes)} duplicate holdout touches" if dupes else "no duplicate holdout touches",
        )
    else:
        # Ledger may not exist yet if no confirmation stage has run
        gate.check("holdout-ledger-consistent", True, "no holdout ledger yet (pre-confirmation)")

    # Check 5: Funnel self-test passes
    funnel_mod = load_funnel_module(root)
    if funnel_mod and hasattr(funnel_mod, "self_test"):
        try:
            funnel_mod.self_test()
            gate.check("funnel-self-test", True, "funnel.py self_test() passed")
        except (AssertionError, Exception) as e:
            gate.check("funnel-self-test", False, f"funnel self-test failed: {e}")
    elif funnel_mod:
        gate.check("funnel-self-test", True, "funnel module loaded (no self_test function)")
    else:
        gate.check("funnel-self-test", False, "funnel.py not found")

    # Stage code recorded (axiom 5 — reproducibility)
    check_stage_code(gate, root, "fde")

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
