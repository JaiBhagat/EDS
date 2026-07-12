#!/usr/bin/env python3
"""EDS state helper — data-manifest.json.

Records path/hash/rowcount/time-range per source at last audit.
Session init diffs current data against it and reopens affected stages
on out-of-tolerance drift.

Usage:
    python manifest.py register <path.csv> [--manifest .eds/data-manifest.json]
    python manifest.py diff [--manifest .eds/data-manifest.json]
    python manifest.py show [--manifest .eds/data-manifest.json]
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd


DEFAULT_MANIFEST = ".eds/data-manifest.json"


def _file_hash(path, sample_bytes=1_000_000):
    """Fast hash: first 1MB of the file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(sample_bytes))
    return h.hexdigest()[:16]


def _quick_profile(path, sample_rows=50_000):
    """Quick row count, column count, and date range if detectable."""
    df = pd.read_csv(path, nrows=sample_rows)
    profile = {
        "row_count": len(df),
        "col_count": len(df.columns),
        "columns": list(df.columns),
    }
    # Detect date columns for time range
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower() or col.endswith("_at"):
            try:
                dates = pd.to_datetime(df[col], errors="coerce").dropna()
                if len(dates) > 0:
                    profile["time_col"] = col
                    profile["min_date"] = str(dates.min().date())
                    profile["max_date"] = str(dates.max().date())
                    break
            except Exception:
                continue
    # Check actual row count if file is larger than sample
    try:
        with open(path) as f:
            actual_rows = sum(1 for _ in f) - 1  # subtract header
        if actual_rows > sample_rows:
            profile["row_count"] = actual_rows
            profile["sampled"] = True
    except Exception:
        pass
    return profile


def load_manifest(manifest_path):
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path) as f:
        return json.load(f)


def save_manifest(entries, manifest_path):
    os.makedirs(os.path.dirname(manifest_path) or ".", exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(entries, f, indent=2)


def register_source(data_path, manifest_path=DEFAULT_MANIFEST,
                    rowcount_tolerance=0.05, max_date_advance_days=None):
    """Register or update a data source in the manifest."""
    entries = load_manifest(manifest_path)
    profile = _quick_profile(data_path)
    file_hash = _file_hash(data_path)

    entry = {
        "path": data_path,
        "hash": file_hash,
        "row_count": profile["row_count"],
        "col_count": profile["col_count"],
        "columns": profile["columns"],
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "tolerances": {
            "rowcount_pct": rowcount_tolerance,
            "max_date_advance_days": max_date_advance_days,
        },
    }
    if "time_col" in profile:
        entry["time_col"] = profile["time_col"]
        entry["min_date"] = profile["min_date"]
        entry["max_date"] = profile["max_date"]

    # Update existing or append
    existing_idx = next(
        (i for i, e in enumerate(entries) if e.get("path") == data_path), None
    )
    if existing_idx is not None:
        entries[existing_idx] = entry
    else:
        entries.append(entry)

    save_manifest(entries, manifest_path)
    return entry


def diff_manifest(manifest_path=DEFAULT_MANIFEST):
    """Compare current data against the manifest. Returns list of drift findings."""
    entries = load_manifest(manifest_path)
    findings = []

    for entry in entries:
        data_path = entry.get("path")
        if not data_path or not os.path.exists(data_path):
            findings.append({
                "path": data_path,
                "type": "missing",
                "detail": "file not found at registered path",
                "severity": "error",
            })
            continue

        current_hash = _file_hash(data_path)
        if current_hash == entry.get("hash"):
            continue  # unchanged

        # File changed — check what drifted
        profile = _quick_profile(data_path)
        old_rows = entry.get("row_count", 0)
        new_rows = profile["row_count"]
        tolerance = entry.get("tolerances", {}).get("rowcount_pct", 0.05)

        if old_rows > 0:
            pct_change = abs(new_rows - old_rows) / old_rows
            if pct_change > tolerance:
                findings.append({
                    "path": data_path,
                    "type": "rowcount_drift",
                    "detail": f"{old_rows} → {new_rows} ({pct_change:+.1%}), tolerance ±{tolerance:.0%}",
                    "severity": "warning" if pct_change < 2 * tolerance else "error",
                })

        if "max_date" in entry and "time_col" in profile:
            old_max = entry["max_date"]
            new_max = profile.get("max_date")
            if new_max and new_max != old_max:
                findings.append({
                    "path": data_path,
                    "type": "time_range_change",
                    "detail": f"max date {old_max} → {new_max}",
                    "severity": "info",
                })

        if current_hash != entry.get("hash"):
            findings.append({
                "path": data_path,
                "type": "content_changed",
                "detail": f"hash {entry.get('hash')} → {current_hash}",
                "severity": "info",
            })

    return findings


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    reg = sub.add_parser("register")
    reg.add_argument("path")
    reg.add_argument("--manifest", default=DEFAULT_MANIFEST)
    reg.add_argument("--rowcount-tolerance", type=float, default=0.05)

    diff_cmd = sub.add_parser("diff")
    diff_cmd.add_argument("--manifest", default=DEFAULT_MANIFEST)

    show_cmd = sub.add_parser("show")
    show_cmd.add_argument("--manifest", default=DEFAULT_MANIFEST)

    args = ap.parse_args()

    if args.cmd == "register":
        entry = register_source(args.path, args.manifest, args.rowcount_tolerance)
        print(f"Registered: {entry['path']} ({entry['row_count']} rows, hash={entry['hash']})")

    elif args.cmd == "diff":
        findings = diff_manifest(args.manifest)
        if not findings:
            print("No drift detected — all sources match manifest.")
        else:
            for f in findings:
                print(f"[{f['severity']}] {f['path']}: {f['type']} — {f['detail']}")

    elif args.cmd == "show":
        entries = load_manifest(args.manifest)
        for e in entries:
            time_info = f", {e.get('time_col','')}: {e.get('min_date','')}..{e.get('max_date','')}" if e.get("time_col") else ""
            print(f"  {e['path']}: {e['row_count']} rows, {e['col_count']} cols{time_info} (audited {e['audited_at'][:10]})")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
