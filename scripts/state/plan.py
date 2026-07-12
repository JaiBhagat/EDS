#!/usr/bin/env python3
"""EDS state helper — Plan section management in BRIEF.md.

Handles Plan status transitions (H4: append-only with actor + reason).
All Plan mutations go through this module — no ad-hoc regex edits.

Usage:
    python plan.py status [--brief .eds/BRIEF.md]
    python plan.py transition <stage> <new-status> \
        [--reason <reason>] [--gate-record <path>] [--brief .eds/BRIEF.md]
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone


DEFAULT_BRIEF = ".eds/BRIEF.md"

VALID_STATUSES = {"pending", "in-progress", "done", "skipped"}

# Plan entry pattern: "- <stage> · <skill> · <status> · <gate>"
PLAN_ENTRY_RE = re.compile(
    r"^(\s*[-*]\s+)(\S+)\s*·\s*(\S+)\s*·\s*(\S+(?:\s*—\s*.+?)?)\s*·\s*(.*)$"
)


def parse_plan(brief_text):
    """Extract Plan entries from BRIEF.md text."""
    plan_idx = brief_text.find("## Plan")
    if plan_idx == -1:
        return None, []

    plan_text = brief_text[plan_idx:]
    # Find the end of the Plan section (next ## or end of file)
    next_section = re.search(r"\n## (?!Plan)", plan_text[1:])
    if next_section:
        plan_text = plan_text[:next_section.start() + 1]

    entries = []
    for line in plan_text.split("\n"):
        m = PLAN_ENTRY_RE.match(line)
        if m:
            prefix, stage, skill, status, gate = m.groups()
            entries.append({
                "stage": stage,
                "skill": skill,
                "status": status.strip(),
                "gate": gate.strip(),
                "raw_line": line,
            })
    return plan_text, entries


def get_status(brief_path=DEFAULT_BRIEF):
    """Return parsed Plan status."""
    if not os.path.exists(brief_path):
        return None

    brief = open(brief_path, encoding="utf-8").read()
    _, entries = parse_plan(brief)
    if not entries:
        return None

    done = sum(1 for e in entries if "done" in e["status"].lower())
    skipped = sum(1 for e in entries if "skipped" in e["status"].lower())
    total = len(entries) - skipped

    current = next((e for e in entries if "in-progress" in e["status"].lower()), None)
    next_pending = next((e for e in entries if e["status"].strip().lower() == "pending"), None)

    return {
        "done": done,
        "total": total,
        "skipped": skipped,
        "current": current,
        "next_pending": next_pending,
        "entries": entries,
    }


def transition_stage(brief_path, stage_name, new_status, reason=None, gate_record=None):
    """Update a stage's status in the Plan. Append-only semantics (H4)."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Valid: {VALID_STATUSES}")

    brief = open(brief_path, encoding="utf-8").read()
    _, entries = parse_plan(brief)

    target = next((e for e in entries if e["stage"] == stage_name), None)
    if not target:
        raise ValueError(f"Stage '{stage_name}' not found in Plan")

    # Build the new status string
    new_status_str = new_status
    if new_status == "skipped" and reason:
        new_status_str = f"skipped — {reason}"

    # Build the new gate string
    new_gate = target["gate"]
    if gate_record and new_status == "done":
        new_gate = f"gate-record: {gate_record}"

    # Build the replacement line
    old_line = target["raw_line"]
    m = PLAN_ENTRY_RE.match(old_line)
    if not m:
        raise ValueError(f"Cannot parse Plan entry: {old_line}")

    prefix = m.group(1)
    new_line = f"{prefix}{target['stage']} · {target['skill']} · {new_status_str} · {new_gate}"

    brief = brief.replace(old_line, new_line)
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(brief)

    # Write .current-stage sidecar so ds-lint scope-guard can read one line
    # instead of parsing BRIEF.md on every edit
    _update_current_stage_cache(brief_path, brief)

    return {"stage": stage_name, "old_status": target["status"], "new_status": new_status_str}


def _update_current_stage_cache(brief_path, brief_text=None):
    """Write .eds/.current-stage with the first in-progress stage name."""
    eds_dir = os.path.dirname(brief_path)
    cache_path = os.path.join(eds_dir, ".current-stage")
    if brief_text is None:
        brief_text = open(brief_path, encoding="utf-8").read()
    _, entries = parse_plan(brief_text)
    current = next((e["stage"] for e in entries if "in-progress" in e["status"].lower()), "")
    try:
        with open(cache_path, "w") as f:
            f.write(current)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    status_cmd = sub.add_parser("status")
    status_cmd.add_argument("--brief", default=DEFAULT_BRIEF)

    trans_cmd = sub.add_parser("transition")
    trans_cmd.add_argument("stage")
    trans_cmd.add_argument("new_status")
    trans_cmd.add_argument("--reason")
    trans_cmd.add_argument("--gate-record")
    trans_cmd.add_argument("--brief", default=DEFAULT_BRIEF)

    args = ap.parse_args()

    if args.cmd == "status":
        status = get_status(args.brief)
        if not status:
            print("No Plan found.")
            return
        print(f"Plan: {status['done']}/{status['total']} done", end="")
        if status["current"]:
            print(f" · current: {status['current']['stage']}", end="")
        if status["next_pending"]:
            print(f" · next: {status['next_pending']['stage']}", end="")
        print()
        for e in status["entries"]:
            mark = "+" if "done" in e["status"].lower() else ("-" if "skip" in e["status"].lower() else " ")
            print(f"  [{mark}] {e['stage']} · {e['skill']} · {e['status']}")

    elif args.cmd == "transition":
        result = transition_stage(
            args.brief, args.stage, args.new_status,
            reason=args.reason, gate_record=args.gate_record,
        )
        print(f"Transitioned {result['stage']}: {result['old_status']} → {result['new_status']}")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
