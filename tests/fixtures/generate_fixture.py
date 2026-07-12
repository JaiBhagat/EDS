#!/usr/bin/env python3
"""Generate the synthetic fixture project for regression tests.

Creates:
- fixture_data.csv — imbalanced binary target (~1% positive), numeric + categorical cols
- fixture_secondary.csv — a joinable secondary source (by entity_id)
- .eds/BRIEF.md — stub Brief with Primary metric = Average Precision (AUPRC)

Run once to regenerate; the CSV is checked in so tests don't depend on this script.
"""
import json
import os

import numpy as np
import pandas as pd

SEED = 42
N = 5000
POSITIVE_RATE = 0.01

rng = np.random.default_rng(SEED)

# Primary table
entity_ids = [f"E{i:05d}" for i in range(N)]
dates = pd.date_range("2023-01-01", periods=N, freq="h")

signal_a = rng.normal(0, 1, N)
signal_b = rng.normal(0, 1, N)
noise_c = rng.normal(0, 1, N)
cat_d = rng.choice(["alpha", "beta", "gamma", "delta"], N)
high_null = np.where(rng.random(N) < 0.85, np.nan, rng.normal(0, 1, N))
near_constant = np.where(rng.random(N) < 0.995, 0, 1)

# Imbalanced target: ~1% positive, driven by signal_a + signal_b
logit = -4.5 + 1.5 * signal_a + 1.0 * signal_b
prob = 1 / (1 + np.exp(-logit))
target = rng.binomial(1, prob)

df = pd.DataFrame({
    "entity_id": entity_ids,
    "event_date": dates,
    "signal_a": np.round(signal_a, 4),
    "signal_b": np.round(signal_b, 4),
    "noise_c": np.round(noise_c, 4),
    "cat_d": cat_d,
    "high_null_col": np.round(high_null, 4),
    "near_constant_col": near_constant,
    "target": target,
})

out_dir = os.path.dirname(__file__)
df.to_csv(os.path.join(out_dir, "fixture_data.csv"), index=False)

# Secondary table (joinable by entity_id)
sec_ids = rng.choice(entity_ids, size=N // 2, replace=False)
df_sec = pd.DataFrame({
    "entity_id": sec_ids,
    "sec_feature_x": np.round(rng.normal(0, 1, len(sec_ids)), 4),
    "sec_feature_y": rng.choice(["low", "mid", "high"], len(sec_ids)),
})
df_sec.to_csv(os.path.join(out_dir, "fixture_secondary.csv"), index=False)

# Stub Brief
brief_dir = os.path.join(out_dir, "eds_fixture", ".eds")
os.makedirs(brief_dir, exist_ok=True)
brief = """\
# Problem Brief — Fixture Project

## Stage 5: Success metric & baseline bar

| Field | Value |
|---|---|
| Primary metric | **Average Precision (AUPRC)** |
| Baseline bar | 0.05 |
| Cost asymmetry | FN >> FP (missing a positive is 10x worse) |

## Plan

| stage | status | gate |
|---|---|---|
| data-audit | done | gate:data-audit-20240101 |
| eda | done | gate:eda-20240101 |
| evaluation-design | done | gate:eval-20240101 |
| baseline | pending | |
| fde | pending | |
| model | pending | |
"""
with open(os.path.join(brief_dir, "BRIEF.md"), "w") as f:
    f.write(brief)

print(f"Fixture generated: {N} rows, positive rate = {target.mean():.3f}")
print(f"  primary: {os.path.join(out_dir, 'fixture_data.csv')}")
print(f"  secondary: {os.path.join(out_dir, 'fixture_secondary.csv')}")
print(f"  brief: {os.path.join(brief_dir, 'BRIEF.md')}")
