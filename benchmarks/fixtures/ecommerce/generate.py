#!/usr/bin/env python3
"""Generates the ecommerce benchmark fixture — deterministic, seeded.

Usage: python generate.py

Writes data/{orders,users,events,features}.csv and splits/{train,test}.csv
into this fixture's own directory. Plants defects on purpose (see
../../tasks/_answer-key.md for the full list) — this is a benchmark fixture,
not a template for real analysis code.
"""
import os

import numpy as np
import pandas as pd

SEED = 7
N_USERS = 2000
OBSERVED_UNTIL = pd.Timestamp("2026-06-01")
HERE = os.path.dirname(os.path.abspath(__file__))


def gen_users(rng):
    signup = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 700, N_USERS), unit="D")
    region = rng.choice(["north", "south", "east", "west"], N_USERS, p=[0.3, 0.3, 0.2, 0.2])
    plan = rng.choice(["free", "basic", "pro"], N_USERS, p=[0.5, 0.35, 0.15])

    # true generative process for churn: older signups + free plan skew churned,
    # plus noise. This is what a real model should recover signal from.
    churn_prob = 0.08 + 0.15 * (plan == "free") + 0.05 * ((OBSERVED_UNTIL - signup).days > 400)
    churned = (rng.random(N_USERS) < churn_prob).astype(int)

    df = pd.DataFrame({
        "user_id": range(1, N_USERS + 1),
        "signup_date": signup,
        "region": region,
        "plan": plan,
        "churned": churned,
    })
    return df


def gen_leak_feature(users, rng):
    """DEFECT 2 (target leakage): account_closed_reason is only ever populated
    for churned users (it's recorded at cancellation time) — it's the target
    encoded as a feature, not a predictor of it."""
    reasons = rng.choice(["price", "missing_feature", "support_issue", "competitor"], len(users))
    account_closed_reason = np.where(users["churned"] == 1, reasons, None)
    return pd.DataFrame({"user_id": users["user_id"], "account_closed_reason": account_closed_reason})


def gen_orders(users, rng):
    rows = []
    order_id = 1
    for _, u in users.iterrows():
        n_orders = rng.poisson(3 if u["churned"] == 0 else 1)
        for _ in range(n_orders):
            days_active = max((OBSERVED_UNTIL - u["signup_date"]).days, 1)
            order_date = u["signup_date"] + pd.to_timedelta(rng.integers(0, days_active), unit="D")
            rows.append({
                "order_id": order_id,
                "user_id": u["user_id"],
                "order_date": order_date,
                "amount": round(float(rng.gamma(2, 25)), 2),
                "status": "completed",
            })
            order_id += 1
    df = pd.DataFrame(rows)

    # DEFECT 1 (duplicated rows): ~2% of rows duplicated exactly, same order_id.
    n_dupes = max(1, int(len(df) * 0.02))
    dupes = df.sample(n=n_dupes, random_state=SEED)
    df = pd.concat([df, dupes], ignore_index=True)
    return df


def gen_events(users, rng):
    rows = []
    event_id = 1
    for _, u in users.iterrows():
        n_events = rng.poisson(8)
        for _ in range(n_events):
            days_active = max((OBSERVED_UNTIL - u["signup_date"]).days, 1)
            event_time = u["signup_date"] + pd.to_timedelta(rng.integers(0, days_active), unit="D")
            rows.append({
                "event_id": event_id,
                "user_id": u["user_id"],
                "event_type": rng.choice(["login", "view_item", "add_to_cart", "support_ticket"]),
                "event_time": event_time,
            })
            event_id += 1
    return pd.DataFrame(rows)


def gen_splits(users, rng):
    """DEFECT 3 (entity-overlapping split): ~10% of test users are also in
    train — a random split on user_id ignoring that some users appear
    multiple times across the modeling table."""
    shuffled = users.sample(frac=1, random_state=SEED)
    cut = int(len(shuffled) * 0.8)
    train_users = shuffled.iloc[:cut]
    test_users = shuffled.iloc[cut:]
    overlap_n = max(1, int(len(test_users) * 0.10))
    overlap_ids = train_users["user_id"].sample(n=overlap_n, random_state=SEED).tolist()
    test_users = pd.concat([test_users, users[users["user_id"].isin(overlap_ids)]], ignore_index=True)
    return train_users, test_users


def main():
    rng = np.random.default_rng(SEED)
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "splits"), exist_ok=True)

    users = gen_users(rng)
    leak = gen_leak_feature(users, rng)
    orders = gen_orders(users, rng)
    events = gen_events(users, rng)
    train_users, test_users = gen_splits(users, rng)

    users.to_csv(os.path.join(HERE, "data", "users.csv"), index=False)
    orders.to_csv(os.path.join(HERE, "data", "orders.csv"), index=False)
    events.to_csv(os.path.join(HERE, "data", "events.csv"), index=False)
    leak.to_csv(os.path.join(HERE, "data", "features.csv"), index=False)
    train_users.to_csv(os.path.join(HERE, "splits", "train.csv"), index=False)
    test_users.to_csv(os.path.join(HERE, "splits", "test.csv"), index=False)

    print(f"users={len(users)} orders={len(orders)} events={len(events)} "
          f"train={len(train_users)} test={len(test_users)} "
          f"churn_rate={users['churned'].mean():.3f}")


if __name__ == "__main__":
    main()
