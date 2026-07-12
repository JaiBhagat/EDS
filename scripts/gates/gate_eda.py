#!/usr/bin/env python3
"""EDS gate: eda.

Checks:
- EDA findings exist (in notebooks, .eds/ artifacts, or markdown)
- Every finding line carries a probe-output reference (evidence-backed)
- No orphan claims (assertions without supporting data reference)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, check_stage_code, find_eds_root

# Patterns that indicate an evidence reference
EVIDENCE_REF_RE = re.compile(
    r"(probe:|output:|fig[ure]*[\s:_]|plot[\s:_]|\.png|\.svg|\.csv|"
    r"cell\s*\d|notebook|\.ipynb|data shows|p[<>=]|n\s*=\s*\d|"
    r"mean\s*=|median\s*=|std\s*=|corr\s*=|\d+%|\d+\.\d+)",
    re.IGNORECASE,
)

# Pattern for finding-like assertions
FINDING_RE = re.compile(
    r"^[-*]\s+.{15,}",  # bullet points with substantial content
    re.MULTILINE,
)


def find_eda_artifacts(root: Path) -> list[Path]:
    """Locate EDA output files."""
    candidates = []
    # Check .eds/ for EDA notes
    eds_dir = root / ".eds"
    for f in eds_dir.glob("*eda*"):
        candidates.append(f)
    for f in eds_dir.glob("*findings*"):
        candidates.append(f)
    # Check notebooks
    for f in root.rglob("*.ipynb"):
        if "eda" in f.name.lower() or "explor" in f.name.lower():
            candidates.append(f)
    # Check markdown reports
    for f in root.rglob("*.md"):
        if "eda" in f.name.lower() or "findings" in f.name.lower():
            if ".eds" not in str(f) or "eda" in f.name.lower():
                candidates.append(f)
    return candidates


def check_findings_have_evidence(text: str) -> tuple[int, int, list[str]]:
    """Return (total_findings, backed_findings, unbacked_list)."""
    findings = FINDING_RE.findall(text)
    total = len(findings)
    unbacked = []
    backed = 0
    for finding in findings:
        if EVIDENCE_REF_RE.search(finding):
            backed += 1
        else:
            unbacked.append(finding[:80])
    return total, backed, unbacked


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("eda")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    artifacts = find_eda_artifacts(root)

    # Check 1: EDA artifacts exist
    gate.check(
        "eda-artifacts-exist",
        len(artifacts) > 0,
        f"{len(artifacts)} EDA artifact(s) found" if artifacts else "no EDA notebooks/files found",
    )

    if not artifacts:
        gate.write_and_exit(root)
        return

    for a in artifacts[:5]:
        gate.add_evidence(str(a))

    # Check 2: Findings carry evidence references
    total_findings = 0
    total_backed = 0
    all_unbacked: list[str] = []

    for artifact in artifacts:
        try:
            text = artifact.read_text(encoding="utf-8", errors="replace")
            t, b, unbacked = check_findings_have_evidence(text)
            total_findings += t
            total_backed += b
            all_unbacked.extend(unbacked[:3])
        except (OSError, UnicodeDecodeError):
            continue

    if total_findings > 0:
        coverage = total_backed / total_findings
        gate.check(
            "findings-evidence-backed",
            coverage >= 0.8,  # 80% threshold
            f"{total_backed}/{total_findings} findings have evidence refs ({coverage:.0%})",
        )
        if all_unbacked:
            gate.check(
                "no-orphan-claims",
                len(all_unbacked) <= 2,
                f"{len(all_unbacked)} unbacked: {all_unbacked[0][:60]}..."
                if all_unbacked
                else "all claims backed",
            )
    else:
        gate.check(
            "findings-evidence-backed",
            False,
            "no finding-like assertions found in EDA artifacts",
        )

    # Stage code recorded (axiom 5 — reproducibility)
    check_stage_code(gate, root, "eda")

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
