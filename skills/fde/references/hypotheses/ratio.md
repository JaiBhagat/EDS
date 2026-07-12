# Ratio

**Claim pattern:** the *relationship* between two quantities — not either alone — carries the signal (utilization, density, share-of-wallet).

**Precondition probe:** the denominator is non-zero and meaningfully bounded across the population; both quantities are point-in-time available.

**Construction recipe:** `numerator / denominator` with an explicit epsilon or zero-handling rule stated up front, not left implicit.

**Canonical failure modes:**
- near-zero denominators produce extreme, unstable ratios that dominate model attention
- the ratio value is ambiguous about scale (0.5 could mean two very different absolute levels) — keep the absolute levels alongside if that ambiguity matters
