#!/usr/bin/env python3
"""EDS — Activity log utility (H7).

Append-only, one line per probe/gate/trial/round. Grep-able, never bulk-loaded.
Format: ISO-ts | actor | action | artifact-path | detail

Usage:
    python activity_log.py append --actor <skill> --action <what> \
        [--artifact <path>] [--detail <msg>] [--log-path .eds/activity.log]

    python activity_log.py tail [--n 20] [--log-path .eds/activity.log]

    python activity_log.py grep <pattern> [--log-path .eds/activity.log]
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone


DEFAULT_LOG_PATH = ".eds/activity.log"


def append_entry(log_path, actor, action, artifact=None, detail=None):
    """Append a single activity line."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [ts, actor, action, artifact or "-", detail or ""]
    line = " | ".join(parts)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def tail_log(log_path, n=20):
    """Print the last n lines."""
    if not os.path.exists(log_path):
        print(f"No activity log at {log_path}")
        return
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-n:]:
        print(line, end="")


def grep_log(log_path, pattern):
    """Grep the log for a pattern."""
    if not os.path.exists(log_path):
        print(f"No activity log at {log_path}")
        return
    regex = re.compile(pattern, re.IGNORECASE)
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            if regex.search(line):
                print(line, end="")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    append_cmd = sub.add_parser("append")
    append_cmd.add_argument("--actor", required=True)
    append_cmd.add_argument("--action", required=True)
    append_cmd.add_argument("--artifact")
    append_cmd.add_argument("--detail")
    append_cmd.add_argument("--log-path", default=DEFAULT_LOG_PATH)

    tail_cmd = sub.add_parser("tail")
    tail_cmd.add_argument("--n", type=int, default=20)
    tail_cmd.add_argument("--log-path", default=DEFAULT_LOG_PATH)

    grep_cmd = sub.add_parser("grep")
    grep_cmd.add_argument("pattern")
    grep_cmd.add_argument("--log-path", default=DEFAULT_LOG_PATH)

    args = ap.parse_args()

    if args.cmd == "append":
        line = append_entry(args.log_path, args.actor, args.action,
                            args.artifact, args.detail)
        print(line)
    elif args.cmd == "tail":
        tail_log(args.log_path, args.n)
    elif args.cmd == "grep":
        grep_log(args.log_path, args.pattern)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
