# Velocity

**Claim pattern:** rate of change over a window predicts outcome beyond the level itself — acceleration or deceleration matters, not just where a value sits.

**Precondition probe:** entity has repeated observations across ≥2 comparable windows so a derivative is even computable; window boundaries respect the availability timeline.

**Construction recipe:** `(value_t - value_t-1) / window`, or the slope of a short rolling regression over the trailing periods.

**Canonical failure modes:**
- divide-by-zero or blown-up ratios near a near-zero baseline
- window too short — noise dominates the "trend"
- sparse-history entities get NaN silently coerced to zero, which changes "unknown" into "no change" without saying so
