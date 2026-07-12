# Seasonality

**Claim pattern:** a recurring calendar pattern (weekly/monthly/annual) predicts outcome beyond a generic time trend.

**Precondition probe:** history spans enough full cycles to distinguish seasonality from a one-off trend (e.g. ≥2 years for an annual claim); the metric visibly cycles on inspection, not just assumed because "seasonality sounds right."

**Construction recipe:** cyclic encoding (sin/cos of period position) or an explicit calendar dummy, fit only on history available at decision time.

**Canonical failure modes:**
- single-cycle history mistaken for seasonality when it's actually a trend or a one-time event
- cyclic encoding period mismatched to the true cycle (fiscal vs. calendar year is the classic version)
