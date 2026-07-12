#!/usr/bin/env python3
"""EDS gate: discovery.

Checks:
- BRIEF.md exists
- Schema-complete (all required sections present)
- Status is 'confirmed'
- Plan section present with at least one stage entry
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_utils import GateResult, find_eds_root, load_brief

REQUIRED_SECTIONS = [
    "## Status",
    "## Decision",
    "## Confirmed problem statement",
    "## Data inventory",
    "## Target & label strategy",
    "## Unit & grain",
    "## Time semantics",
    "## Task type",
    "## Success metric & baseline bar",
]

PLAN_ENTRY_RE = re.compile(
    r"^\s*[-*]\s+\S+.*\b(pending|in-progress|done|skipped)\b",
    re.IGNORECASE | re.MULTILINE,
)


def run(project_dir: str = "."):
    root = find_eds_root(project_dir)
    gate = GateResult("discovery")

    if not root:
        gate.check("eds-root-exists", False, ".eds/ directory not found")
        gate.write_and_exit(Path(project_dir))
        return

    brief = load_brief(root)

    # Check 1: BRIEF.md exists
    if not gate.check("brief-exists", brief is not None, ".eds/BRIEF.md"):
        gate.write_and_exit(root)
        return

    gate.add_evidence(str(root / ".eds" / "BRIEF.md"))

    # Check 2: Schema completeness
    missing = [s for s in REQUIRED_SECTIONS if s not in brief]
    gate.check(
        "schema-complete",
        len(missing) == 0,
        f"missing sections: {missing}" if missing else "all required sections present",
    )

    # Check 3: Status is confirmed
    status_match = re.search(r"^##\s+Status\s*\n(.+?)(?=\n##|\Z)", brief, re.MULTILINE | re.DOTALL)
    if status_match:
        status_block = status_match.group(1).strip().lower()
        is_confirmed = "confirmed" in status_block
        gate.check("status-confirmed", is_confirmed, f"status block: {status_block[:80]}")
    else:
        gate.check("status-confirmed", False, "Status section not parseable")

    # Check 4: Plan section present with entries
    has_plan = "## Plan" in brief
    if has_plan:
        plan_start = brief.index("## Plan")
        plan_text = brief[plan_start:]
        entries = PLAN_ENTRY_RE.findall(plan_text)
        gate.check(
            "plan-present",
            len(entries) > 0,
            f"{len(entries)} plan entries found",
        )
    else:
        gate.check("plan-present", False, "## Plan section missing from BRIEF.md")

    gate.write_and_exit(root)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else ".")
