#!/usr/bin/env python3
"""MDE/FDE — Shared holdout ledger.

Tracks every touch of the project-wide confirmation holdout. Both FDE
(stage 10 confirmation) and MDE (champion confirmation) share this ledger.
The constraint: the confirmation holdout is touched at most once per stage
(M7/F7). A second touch requires an explicit deferred marker.

Usage:
    python holdout_ledger.py touch --stage <stage> --score <value> \
        [--metric roc_auc] [--ledger-path .eds/holdout_ledger.json]

    python holdout_ledger.py check [--ledger-path .eds/holdout_ledger.json]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone


def load_ledger(path):
    if not os.path.exists(path):
        return {"touches": []}
    with open(path) as f:
        return json.load(f)


def save_ledger(ledger, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(ledger, f, indent=2)


def record_touch(ledger_path, stage, score, metric="roc_auc",
                 model_name=None, force=False):
    """Record a holdout touch. Refuses if stage already touched (unless force)."""
    ledger = load_ledger(ledger_path)
    touches = ledger.get("touches", [])

    existing = [t for t in touches if t.get("stage") == stage]
    if existing and not force:
        raise RuntimeError(
            f"Holdout already touched for stage '{stage}' "
            f"(at {existing[0].get('timestamp', '?')}). "
            "A second touch requires '# eds: deferred — holdout re-use'."
        )

    touch = {
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metric": metric,
        "score": score,
        "model_name": model_name,
        "forced": force,
    }
    touches.append(touch)
    ledger["touches"] = touches
    save_ledger(ledger, ledger_path)
    return touch


def check_ledger(ledger_path):
    """Check ledger integrity: no duplicate stage touches without force flag."""
    ledger = load_ledger(ledger_path)
    touches = ledger.get("touches", [])

    issues = []
    stage_counts = {}
    for t in touches:
        stage = t.get("stage", "unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        if stage_counts[stage] > 1 and not t.get("forced"):
            issues.append(f"Stage '{stage}' touched {stage_counts[stage]} times without force flag")

    return issues


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    touch_cmd = sub.add_parser("touch")
    touch_cmd.add_argument("--stage", required=True)
    touch_cmd.add_argument("--score", type=float, required=True)
    touch_cmd.add_argument("--metric", default="roc_auc")
    touch_cmd.add_argument("--model-name")
    touch_cmd.add_argument("--force", action="store_true")
    touch_cmd.add_argument("--ledger-path", default=".eds/holdout_ledger.json")

    check_cmd = sub.add_parser("check")
    check_cmd.add_argument("--ledger-path", default=".eds/holdout_ledger.json")

    args = ap.parse_args()

    if args.cmd == "touch":
        try:
            touch = record_touch(
                args.ledger_path, args.stage, args.score,
                metric=args.metric, model_name=args.model_name,
                force=args.force,
            )
            print(f"Recorded: {touch['stage']} — {touch['metric']}={touch['score']:.4f}")
        except RuntimeError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "check":
        issues = check_ledger(args.ledger_path)
        if issues:
            print("ISSUES:")
            for i in issues:
                print(f"  - {i}")
            sys.exit(1)
        else:
            print("Holdout ledger OK — no duplicate unforced touches")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
