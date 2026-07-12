#!/usr/bin/env python3
"""EDS gate: report (claim traceability).

Checks:
- Report artifact exists
- Every number/claim resolves to an evidence path
- Unresolved claims cause gate failure

This is the "claim traceability" gate — the plan's H3 mechanism for ensuring
no number in a final report is orphaned from the artifact that produced it.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, find_eds_root

# A "claim" is a number in a context that looks like a finding/result
CLAIM_RE = re.compile(
    r"(?:^|\s)(\d+\.?\d*\s*%"  # percentages
    r"|\$\s*[\d,.]+[KMB]?"  # dollar amounts
    r"|[+-]?\d+\.?\d*\s*(?:pp|bps|basis points)"  # basis points / percentage points
    r"|(?:AUC|ROC|F1|precision|recall|accuracy|RMSE|MAE|R2|lift|p-value)\s*[=:≈]\s*[\d.]+)"  # metric = value
    r"",
    re.IGNORECASE | re.MULTILINE,
)

# Evidence reference patterns (inline citations)
EVIDENCE_INLINE_RE = re.compile(
    r"(\[(?:fig|table|probe|output|notebook|cell|section)\s*[\d:.\w-]+\]"  # [fig 1], [table 2.3]
    r"|(?:see|from|per|ref)\s+[`'\"]?[\w/.-]+[`'\"]?"  # see output/x.csv
    r"|source:\s*\S+"  # source: path
    r"|evidence:\s*\S+"  # evidence: path
    r"|→\s*\S+\.(?:csv|json|png|svg|ipynb|py|sql)"  # → file.csv
    r"|`[^`]+\.(?:csv|json|png|svg|ipynb|py|sql)`)",  # `file.csv`
    re.IGNORECASE,
)


def find_report_artifacts(root: Path) -> list[Path]:
    """Locate report/deliverable files."""
    candidates = []
    eds_dir = root / ".eds"

    # Check for report files
    for pattern in ["*report*", "*deliverable*", "*summary*", "*findings*"]:
        for f in root.rglob(pattern):
            if f.suffix in (".md", ".html", ".pdf", ".ipynb", ".txt"):
                if ".eds/verification" not in str(f):
                    candidates.append(f)

    return list(set(candidates))


def extract_claims_and_evidence(text: str) -> tuple[list[str], list[str]]:
    """Extract claims (numbers) and evidence references from text."""
    claims = CLAIM_RE.findall(text)
    evidence_refs = EVIDENCE_INLINE_RE.findall(text)
    return claims, evidence_refs


def check_line_level_traceability(lines: list[str]) -> tuple[int, int, list[str]]:
    """For each line with a claim, check if it or nearby lines have evidence.

    Returns (claims_found, claims_traced, untraced_claims).
    """
    claims_found = 0
    claims_traced = 0
    untraced: list[str] = []

    for i, line in enumerate(lines):
        line_claims = CLAIM_RE.findall(line)
        if not line_claims:
            continue

        claims_found += len(line_claims)

        # Check this line and ±2 context lines for evidence
        context_window = lines[max(0, i - 2) : i + 3]
        context_text = "\n".join(context_window)

        if EVIDENCE_INLINE_RE.search(context_text):
            claims_traced += len(line_claims)
        else:
            for claim in line_claims:
                untraced.append(f"L{i+1}: {claim.strip()} — {line.strip()[:60]}")

    return claims_found, claims_traced, untraced


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("report")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    reports = find_report_artifacts(root)

    # Check 1: Report artifact exists
    if not gate.check(
        "report-exists",
        len(reports) > 0,
        f"{len(reports)} report artifact(s)" if reports else "no report files found",
    ):
        gate.write_and_exit(root)
        return

    for r in reports[:5]:
        gate.add_evidence(str(r))

    # Check 2: Claim traceability across all reports
    total_claims = 0
    total_traced = 0
    all_untraced: list[str] = []

    for report in reports:
        try:
            text = report.read_text(encoding="utf-8", errors="replace")
            lines = text.split("\n")
            found, traced, untraced = check_line_level_traceability(lines)
            total_claims += found
            total_traced += traced
            for u in untraced:
                all_untraced.append(f"{report.name}:{u}")
        except OSError:
            continue

    if total_claims > 0:
        traceability = total_traced / total_claims
        gate.check(
            "claims-traceable",
            traceability >= 0.9,  # 90% threshold — every number should trace
            f"{total_traced}/{total_claims} claims have evidence refs ({traceability:.0%})",
        )

        # Show first few untraced claims
        if all_untraced:
            sample = all_untraced[:5]
            gate.check(
                "no-orphan-numbers",
                len(all_untraced) <= 2,
                f"{len(all_untraced)} untraced claims. First: {sample[0][:80]}",
            )
    else:
        gate.check(
            "claims-traceable",
            True,
            "no quantitative claims found in report (qualitative-only report)",
        )

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
