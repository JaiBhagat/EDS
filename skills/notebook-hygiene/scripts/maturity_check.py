#!/usr/bin/env python3
"""Probe: promotion-readiness signals for a Jupyter notebook.

Usage:
    python maturity_check.py <notebook.ipynb>

Parses the .ipynb JSON directly (stdlib json — no nbformat dependency
needed for a read-only scan) and flags: hardcoded absolute paths, presence
of a seed, function-definition count, and out-of-order execution counts.
Reports signals only — the SKILL.md decides what target rung they imply.
"""
import argparse
import json
import re

HARDCODED_PATH_RE = re.compile(r"""["'](/Users/|/home/|[A-Za-z]:\\)[^"']*["']""")
SEED_RE = re.compile(r"\b(random_state\s*=|np\.random\.seed|random\.seed|seed\s*=)\b")
DEF_RE = re.compile(r"^\s*def\s+\w+\(", re.MULTILINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook")
    args = ap.parse_args()

    with open(args.notebook, "r", encoding="utf-8") as f:
        nb = json.load(f)

    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    print(f"## maturity_check: {args.notebook} ({len(code_cells)} code cells)")

    all_source = "\n".join("".join(c.get("source", [])) for c in code_cells)
    hardcoded_paths = HARDCODED_PATH_RE.findall(all_source)
    has_seed = bool(SEED_RE.search(all_source))
    n_functions = len(DEF_RE.findall(all_source))

    exec_counts = [c.get("execution_count") for c in code_cells if c.get("execution_count") is not None]
    in_order = exec_counts == sorted(exec_counts)

    print(f"- hardcoded absolute paths: {len(hardcoded_paths)}")
    print(f"- seed present: {'yes' if has_seed else 'no'}")
    print(f"- functions defined: {n_functions}")
    print(f"- execution order: {'in-order' if in_order else 'out-of-order (fine for rung 1, a smell at rung 2+)'}")

    blockers = []
    if hardcoded_paths:
        blockers.append(f"{len(hardcoded_paths)} hardcoded path(s) — move to top-of-file parameters")
    if not has_seed:
        blockers.append("no seed found — required before rung 3 (never-cut item 5)")
    if n_functions == 0 and len(code_cells) > 5:
        blockers.append("no functions defined despite notebook size — likely copy-paste, a rung-2 smell")

    if blockers:
        print("- promotion blockers:")
        for b in blockers:
            print(f"  - {b}")
    else:
        print("- no promotion blockers found")


if __name__ == "__main__":
    main()
