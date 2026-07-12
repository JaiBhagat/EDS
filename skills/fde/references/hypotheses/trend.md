# Trend

**Claim pattern:** the direction/shape of a value over a longer history — not just its latest velocity — predicts outcome (a multi-period slope, a regime change).

**Precondition probe:** enough historical periods per entity to fit a trend without overfitting noise (rule of thumb: ≥5 points); no known structural break mid-window that a single slope would misrepresent.

**Construction recipe:** linear or robust regression slope over N trailing periods, or an explicit change-point flag.

**Canonical failure modes:**
- trend fit dominated by a single outlier period
- trend window silently crosses a known regime change (e.g. a pricing change) that should be its own flag rather than smoothed into a slope
