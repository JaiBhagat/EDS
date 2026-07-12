#!/usr/bin/env python3
"""Records the code/commands actually executed for each Plan stage, so
notebook-assembly can assemble a real notebook instead of stubs.

Written to .eds/stage_code/<stage>.json:
{
  "stage": "eda",
  "recorded_at": "...",
  "cells": [
      {"kind": "code", "source": "df = pd.read_csv(...)\\n...", "note": "load + audit"},
      {"kind": "markdown", "source": "### Q: does <feature> separate the target classes?..."}
  ]
}

Usage:
    python scripts/lib/stage_code.py record --stage eda --cells-json '[...]'
    python scripts/lib/stage_code.py load --stage eda
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone


def record(stage: str, cells: list[dict], eds_root: str = ".eds") -> str:
    """Write stage code cells. Append-only per stage, last write wins."""
    out_dir = os.path.join(eds_root, "stage_code")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{stage}.json")
    data = {
        "stage": stage,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "cells": cells,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def load(stage: str, eds_root: str = ".eds") -> dict | None:
    """Load recorded stage code. Returns None if not found."""
    path = os.path.join(eds_root, "stage_code", f"{stage}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage code recorder for notebook assembly")
    sub = ap.add_subparsers(dest="cmd")

    rec = sub.add_parser("record", help="Record code cells for a stage")
    rec.add_argument("--stage", required=True, help="Stage name (e.g. eda, data-audit)")
    rec.add_argument("--cells-json", required=True,
                     help="JSON array of {kind, source, note?} cell dicts")
    rec.add_argument("--eds-root", default=".eds")

    ld = sub.add_parser("load", help="Load recorded code for a stage")
    ld.add_argument("--stage", required=True)
    ld.add_argument("--eds-root", default=".eds")

    args = ap.parse_args()

    if args.cmd == "record":
        cells = json.loads(args.cells_json)
        path = record(args.stage, cells, args.eds_root)
        print(f"Recorded {len(cells)} cell(s) for stage '{args.stage}' → {path}")

    elif args.cmd == "load":
        data = load(args.stage, args.eds_root)
        if data:
            print(json.dumps(data, indent=2))
        else:
            print(f"No recorded code for stage '{args.stage}'", file=sys.stderr)
            sys.exit(1)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
