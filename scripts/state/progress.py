#!/usr/bin/env python3
"""EDS state helper — progress.md handoff notes.

Manages the structured end-of-session handoff block in .eds/progress.md.
H6: every session leaves a clean restart path.

Usage:
    python progress.py write-handoff --current-stage <stage> \
        [--completed <stages>] [--in-flight <stage:resume-point>] \
        [--broken <items>] [--next-action <action>] \
        [--progress-path .eds/progress.md]

    python progress.py read-latest [--progress-path .eds/progress.md]
"""
import argparse
import os
import re
from datetime import datetime, timezone


DEFAULT_PROGRESS = ".eds/progress.md"


def write_handoff(progress_path, current_stage, completed=None,
                  in_flight=None, broken=None, next_action=None):
    """Append a structured handoff block."""
    os.makedirs(os.path.dirname(progress_path) or ".", exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = f"\n## Handoff — {ts}\n\n"
    block += f"- **Current stage:** {current_stage}\n"

    if completed:
        for item in completed:
            block += f"- **Completed:** {item}\n"

    if in_flight:
        block += f"- **In-flight:** {in_flight}\n"

    if broken:
        for item in broken:
            block += f"- **Broken/unverified:** {item}\n"

    block += f"- **Next action:** {next_action or 'continue from current stage'}\n"

    # Append or create
    if os.path.exists(progress_path):
        with open(progress_path, "a", encoding="utf-8") as f:
            f.write(block)
    else:
        header = "# EDS session progress\n\nAppend-only log of session handoffs.\n"
        with open(progress_path, "w", encoding="utf-8") as f:
            f.write(header + block)

    return block


def read_latest_handoff(progress_path=DEFAULT_PROGRESS):
    """Read the most recent handoff block."""
    if not os.path.exists(progress_path):
        return None

    text = open(progress_path, encoding="utf-8").read()
    blocks = re.split(r"(?=^## Handoff —)", text, flags=re.MULTILINE)
    handoff_blocks = [b for b in blocks if b.strip().startswith("## Handoff")]

    if not handoff_blocks:
        return None

    latest = handoff_blocks[-1].strip()
    # Parse into structured dict
    result = {"raw": latest}
    for line in latest.split("\n"):
        line = line.strip()
        if line.startswith("- **Current stage:**"):
            result["current_stage"] = line.split(":**", 1)[1].strip()
        elif line.startswith("- **In-flight:**"):
            result["in_flight"] = line.split(":**", 1)[1].strip()
        elif line.startswith("- **Next action:**"):
            result["next_action"] = line.split(":**", 1)[1].strip()
        elif line.startswith("- **Completed:**"):
            result.setdefault("completed", []).append(line.split(":**", 1)[1].strip())
        elif line.startswith("- **Broken"):
            result.setdefault("broken", []).append(line.split(":**", 1)[1].strip())

    return result


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    write_cmd = sub.add_parser("write-handoff")
    write_cmd.add_argument("--current-stage", required=True)
    write_cmd.add_argument("--completed", nargs="*")
    write_cmd.add_argument("--in-flight")
    write_cmd.add_argument("--broken", nargs="*")
    write_cmd.add_argument("--next-action")
    write_cmd.add_argument("--progress-path", default=DEFAULT_PROGRESS)

    read_cmd = sub.add_parser("read-latest")
    read_cmd.add_argument("--progress-path", default=DEFAULT_PROGRESS)

    args = ap.parse_args()

    if args.cmd == "write-handoff":
        block = write_handoff(
            args.progress_path, args.current_stage,
            completed=args.completed, in_flight=args.in_flight,
            broken=args.broken, next_action=args.next_action,
        )
        print(block)

    elif args.cmd == "read-latest":
        handoff = read_latest_handoff(args.progress_path)
        if handoff:
            print(handoff["raw"])
        else:
            print("No handoff block found.")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
