#!/usr/bin/env python3
"""EDS FDE — feature_catalog.json read/write/dedupe utilities.

Schema per skills/fde/references/artifacts-schema.md:
{name, family, hypothesis_id, code_ref, construction_hash, data_version,
 availability, cost, online_available, status, sessions_open, evidence}
"""
import json
import os
import hashlib


def load_catalog(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_catalog(path, entries):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def construction_hash(code_text):
    return hashlib.sha256(code_text.encode()).hexdigest()[:12]


def find_duplicate(entries, name=None, construction_text=None):
    """Name match or identical construction-hash match — a duplicate isn't
    always a renamed copy, so both checks matter."""
    chash = construction_hash(construction_text) if construction_text else None
    for e in entries:
        if name and e.get("name") == name:
            return e
        if chash and e.get("construction_hash") == chash:
            return e
    return None


def add_feature(path, entry, construction_text=None):
    """Returns (entry, added: bool). Refuses to add a duplicate silently —
    caller decides what to do with the existing entry instead."""
    entries = load_catalog(path)
    if construction_text:
        entry["construction_hash"] = construction_hash(construction_text)
    dup = find_duplicate(entries, name=entry.get("name"), construction_text=construction_text)
    if dup:
        return dup, False
    entries.append(entry)
    save_catalog(path, entries)
    return entry, True


def stale_candidates(entries, max_sessions=5):
    return [e for e in entries if e.get("status") == "candidate" and e.get("sessions_open", 0) >= max_sessions]


def _demo():
    tmp_path = "/tmp/eds_catalog_selftest.json"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    entry_a = {"name": "user_txn_count_7d", "family": "frequency", "status": "candidate", "sessions_open": 1}
    added, was_new = add_feature(tmp_path, entry_a, construction_text="df.groupby('user_id')['txn'].count()")
    assert was_new is True

    # same name, different construction -> still a name-duplicate, not added
    entry_b = {"name": "user_txn_count_7d", "family": "frequency", "status": "candidate"}
    dup, was_new2 = add_feature(tmp_path, entry_b, construction_text="something else entirely")
    assert was_new2 is False
    assert dup["name"] == "user_txn_count_7d"

    # different name, identical construction -> caught by hash match
    entry_c = {"name": "renamed_but_same_code", "family": "frequency", "status": "candidate"}
    dup2, was_new3 = add_feature(tmp_path, entry_c, construction_text="df.groupby('user_id')['txn'].count()")
    assert was_new3 is False

    entries = load_catalog(tmp_path)
    assert len(entries) == 1

    stale = stale_candidates([{"name": "x", "status": "candidate", "sessions_open": 6}], max_sessions=5)
    assert len(stale) == 1

    os.remove(tmp_path)
    print("catalog.py self-test OK")


if __name__ == "__main__":
    _demo()
