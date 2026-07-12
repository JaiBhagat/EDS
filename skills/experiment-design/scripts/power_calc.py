#!/usr/bin/env python3
"""Probe: sample size / MDE calc for a two-arm experiment.

Usage:
    # required sample size per arm, given the MDE you want to detect
    python power_calc.py --baseline 0.10 --mde 0.02 --metric-type proportion
    python power_calc.py --baseline 50 --mde 5 --metric-type mean --std 20

    # detectable MDE given the sample size you actually have
    python power_calc.py --baseline 0.10 --metric-type proportion --observed-n 5000

Two-sided z-test approximation (standard for A/B sizing). --mde is absolute
(same units as --baseline/--std), not relative, unless --mde-relative is set.
"""
import argparse

from scipy.stats import norm


def sample_size_proportion(p, mde, alpha, power):
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    p2 = p + mde
    pooled_var = p * (1 - p) + p2 * (1 - p2)
    return pooled_var * (z_alpha + z_power) ** 2 / (mde ** 2)


def sample_size_mean(std, mde, alpha, power):
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    return 2 * (std ** 2) * (z_alpha + z_power) ** 2 / (mde ** 2)


def detectable_mde_proportion(p, n, alpha, power):
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    # solve mde from sample_size_proportion by treating pooled_var as ~2p(1-p)
    # (mde is typically small relative to p) then refine once.
    var_guess = 2 * p * (1 - p)
    mde = ((z_alpha + z_power) ** 2 * var_guess / n) ** 0.5
    p2 = p + mde
    pooled_var = p * (1 - p) + p2 * (1 - p2)
    return ((z_alpha + z_power) ** 2 * pooled_var / n) ** 0.5


def detectable_mde_mean(std, n, alpha, power):
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    return ((2 * (std ** 2) * (z_alpha + z_power) ** 2) / n) ** 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=float, required=True, help="baseline rate (proportion) or mean")
    ap.add_argument("--mde", type=float, help="minimum detectable effect, absolute units")
    ap.add_argument("--mde-relative", action="store_true", help="treat --mde as a fraction of --baseline")
    ap.add_argument("--metric-type", choices=["proportion", "mean"], default="proportion")
    ap.add_argument("--std", type=float, help="required for --metric-type mean")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    ap.add_argument("--observed-n", type=int, help="if given, report detectable MDE at this n/arm instead")
    args = ap.parse_args()

    if args.metric_type == "mean" and args.std is None:
        print("FAILED — --metric-type mean requires --std")
        return

    mde = args.mde
    if mde is not None and args.mde_relative:
        mde = args.baseline * mde

    print(f"## power_calc: baseline={args.baseline}, metric={args.metric_type}, alpha={args.alpha}, power={args.power}")

    if args.observed_n:
        if args.metric_type == "proportion":
            detectable = detectable_mde_proportion(args.baseline, args.observed_n, args.alpha, args.power)
        else:
            detectable = detectable_mde_mean(args.std, args.observed_n, args.alpha, args.power)
        print(f"- at n={args.observed_n}/arm: detectable MDE = {detectable:.4g}")
        print("- anything smaller than this is not reliably detectable at this sample size — size the experiment or lower expectations, don't just run it and hope.")
        return

    if mde is None:
        print("FAILED — provide --mde (sizing mode) or --observed-n (detectable-MDE mode)")
        return

    if args.metric_type == "proportion":
        n = sample_size_proportion(args.baseline, mde, args.alpha, args.power)
    else:
        n = sample_size_mean(args.std, mde, args.alpha, args.power)
    print(f"- required sample size: {int(n) + 1} per arm (MDE={mde:.4g})")


if __name__ == "__main__":
    main()
