#!/usr/bin/env python3
"""EDS FDE — feature journal utilities.

The feature journal (feature_journal.md) is an append-only dialogue record:
accept/reject decisions, deliberation rounds, killed families, and the
human's domain input that shaped the campaign.

Usage:
    python journal.py append-deliberation --journal-path .eds/features/feature_journal.md \
        --round 1 --proposed '[...]' --deprioritized '[...]' \
        --user-steer 'Focus on velocity features' --killed '[]' --open-questions '[]'

    python journal.py summarize-deliberations --journal-path .eds/features/feature_journal.md

    python journal.py append-decision --journal-path .eds/features/feature_journal.md \
        --feature <name> --decision accepted --reason '...'
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


def append_deliberation(
    journal_path: str,
    round_num: int,
    proposed: list[dict],
    deprioritized: list[dict],
    user_steer: str,
    killed_families: list[dict] | None = None,
    open_questions: list[str] | None = None,
    prior_evidence: str | None = None,
) -> None:
    """Append a deliberation round to the feature journal."""
    os.makedirs(os.path.dirname(journal_path) or ".", exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [f"\n## Deliberation round {round_num} — {date}\n\n"]

    if prior_evidence:
        lines.append(f"**Evidence from previous round that shaped this one:** {prior_evidence}\n\n")

    lines.append("### Proposed directions\n\n")
    for p in proposed:
        status = p.get("status", "proposed")
        lines.append(f"- **{p.get('family', '?')}** — {p.get('claim', '?')} — "
                      f"cost: {p.get('cost', '?')} — [{status}]\n")

    if deprioritized:
        lines.append("\n### Deprioritized (and why)\n\n")
        for d in deprioritized:
            lines.append(f"- **{d.get('family', '?')}** — {d.get('reason', '?')}\n")

    lines.append(f"\n### User steer\n\n{user_steer}\n")

    if killed_families:
        lines.append("\n### Killed families (and why)\n\n")
        for k in killed_families:
            lines.append(f"- **{k.get('family', '?')}** — {k.get('reason', '?')}\n")

    if open_questions:
        lines.append("\n### Open questions carried forward\n\n")
        for q in open_questions:
            lines.append(f"- {q}\n")

    with open(journal_path, "a", encoding="utf-8") as f:
        f.writelines(lines)


def append_decision(
    journal_path: str,
    feature: str,
    decision: str,
    reason: str,
    round_num: int | None = None,
) -> None:
    """Append a feature accept/reject decision to the journal."""
    os.makedirs(os.path.dirname(journal_path) or ".", exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    round_note = f" (round {round_num})" if round_num else ""

    line = f"\n- [{date}{round_note}] `{feature}` — **{decision}** — {reason}\n"
    with open(journal_path, "a", encoding="utf-8") as f:
        f.write(line)


def summarize_deliberations(journal_path: str) -> str:
    """Extract and print only deliberation entries from the journal.

    Respects the existing "grep, never bulk-load" rule — reads the file
    once but returns only deliberation sections, so a new session can
    catch up on the *thinking* without loading the full journal.
    """
    if not os.path.exists(journal_path):
        return "No journal found."

    with open(journal_path, encoding="utf-8") as f:
        content = f.read()

    # Extract deliberation round sections
    pattern = r"(## Deliberation round \d+.*?)(?=\n## |\Z)"
    matches = re.findall(pattern, content, re.DOTALL)

    if not matches:
        return "No deliberation rounds recorded yet."

    return "\n---\n".join(matches)


def main() -> None:
    ap = argparse.ArgumentParser(description="Feature journal utilities")
    sub = ap.add_subparsers(dest="cmd")

    delib = sub.add_parser("append-deliberation")
    delib.add_argument("--journal-path", default=".eds/features/feature_journal.md")
    delib.add_argument("--round", type=int, required=True)
    delib.add_argument("--proposed", required=True, help="JSON array of {family, claim, cost, status}")
    delib.add_argument("--deprioritized", default="[]", help="JSON array of {family, reason}")
    delib.add_argument("--user-steer", required=True)
    delib.add_argument("--killed", default="[]", help="JSON array of {family, reason}")
    delib.add_argument("--open-questions", default="[]", help="JSON array of strings")
    delib.add_argument("--prior-evidence", default=None)

    dec = sub.add_parser("append-decision")
    dec.add_argument("--journal-path", default=".eds/features/feature_journal.md")
    dec.add_argument("--feature", required=True)
    dec.add_argument("--decision", required=True, choices=["accepted", "rejected", "evicted", "deferred"])
    dec.add_argument("--reason", required=True)
    dec.add_argument("--round", type=int, default=None)

    summ = sub.add_parser("summarize-deliberations")
    summ.add_argument("--journal-path", default=".eds/features/feature_journal.md")

    args = ap.parse_args()

    if args.cmd == "append-deliberation":
        append_deliberation(
            args.journal_path,
            round_num=args.round,
            proposed=json.loads(args.proposed),
            deprioritized=json.loads(args.deprioritized),
            user_steer=args.user_steer,
            killed_families=json.loads(args.killed),
            open_questions=json.loads(args.open_questions),
            prior_evidence=args.prior_evidence,
        )
        print(f"Deliberation round {args.round} appended to {args.journal_path}")

    elif args.cmd == "append-decision":
        append_decision(
            args.journal_path,
            feature=args.feature,
            decision=args.decision,
            reason=args.reason,
            round_num=args.round,
        )
        print(f"Decision for '{args.feature}' appended to {args.journal_path}")

    elif args.cmd == "summarize-deliberations":
        summary = summarize_deliberations(args.journal_path)
        print(summary)

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
