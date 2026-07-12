#!/usr/bin/env python3
"""EDS gate: decision-optimization.

Checks:
- Threshold derivation exists and cites calibration report
- Threshold derivation cites operational capacity
- No test-frame lineage in threshold derivation (thresholds must never be chosen on test data)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, check_stage_code, find_eds_root, load_json

# Patterns indicating test-frame contamination
TEST_FRAME_PATTERNS = re.compile(
    r"\b(X_test|y_test|test_set|test_data|holdout|test_frame|test_df)\b"
    r".*\b(threshold|cutoff|operating_point)\b"
    r"|"
    r"\b(threshold|cutoff|operating_point)\b"
    r".*\b(X_test|y_test|test_set|test_data|holdout|test_frame|test_df)\b",
    re.IGNORECASE,
)

CALIBRATION_REF_RE = re.compile(
    r"(calibrat|platt|isotonic|reliability[_ ]curve|brier|calibration[_ ]report)",
    re.IGNORECASE,
)

CAPACITY_REF_RE = re.compile(
    r"(capacity|queue[_ ]size|review[_ ]volume|throughput|bandwidth|"
    r"agents?[_ ]available|team[_ ]size|operational[_ ]constraint|"
    r"can[_ ]handle|per[_ ]day|per[_ ]week)",
    re.IGNORECASE,
)


def find_threshold_artifacts(root: Path) -> list[Path]:
    """Locate threshold/decision-optimization artifacts."""
    candidates = []
    eds_dir = root / ".eds"

    # Check .eds/ for threshold/decision files
    for pattern in ["*threshold*", "*decision*", "*operating_point*", "*cutoff*"]:
        candidates.extend(eds_dir.rglob(pattern))

    # Check project root for threshold scripts
    for pattern in ["*threshold*", "*decision_opt*"]:
        candidates.extend(root.glob(f"**/{pattern}"))

    # Deduplicate
    return list(set(candidates))


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("decision-optimization")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    artifacts = find_threshold_artifacts(root)

    # Check 1: Threshold derivation exists
    if not gate.check(
        "threshold-derivation-exists",
        len(artifacts) > 0,
        f"{len(artifacts)} threshold artifact(s) found" if artifacts else "no threshold derivation artifacts found",
    ):
        gate.write_and_exit(root)
        return

    for a in artifacts[:5]:
        gate.add_evidence(str(a))

    # Aggregate all threshold artifact content
    all_text = ""
    for artifact in artifacts:
        try:
            all_text += artifact.read_text(encoding="utf-8", errors="replace") + "\n"
        except OSError:
            continue

    # Check 2: Cites calibration
    has_calibration_ref = bool(CALIBRATION_REF_RE.search(all_text))
    gate.check(
        "cites-calibration",
        has_calibration_ref,
        "threshold derivation references calibration"
        if has_calibration_ref
        else "no calibration reference found in threshold artifacts — thresholds require calibrated probabilities",
    )

    # Check 3: Cites operational capacity
    has_capacity_ref = bool(CAPACITY_REF_RE.search(all_text))
    gate.check(
        "cites-capacity",
        has_capacity_ref,
        "threshold derivation references operational capacity"
        if has_capacity_ref
        else "no capacity/operational constraint reference — thresholds must account for review bandwidth (A6)",
    )

    # Check 4: No test-frame lineage
    test_contamination = TEST_FRAME_PATTERNS.findall(all_text)
    gate.check(
        "no-test-frame-lineage",
        len(test_contamination) == 0,
        f"test-frame reference found in threshold derivation — thresholds must NEVER be set on test data"
        if test_contamination
        else "no test-frame contamination detected",
    )

    # Stage code recorded (axiom 5 — reproducibility)
    check_stage_code(gate, root, "decision_optimization")

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
