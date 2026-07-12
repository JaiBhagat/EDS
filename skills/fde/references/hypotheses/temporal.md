# Temporal

**Claim pattern:** *when* something happened (hour, day-of-week, holiday proximity) carries signal beyond *what* happened.

**Precondition probe:** timestamp granularity is fine enough to distinguish the claimed effect; enough volume per time bucket that a bucket's rate isn't noise.

**Construction recipe:** extract hour/day-of-week/is-holiday/days-since-anchor-event from an already-available timestamp.

**Canonical failure modes:**
- timezone inconsistency across sources corrupts the bucketing silently
- bucket too fine-grained (day-of-year) — overfits calendar noise instead of a real cycle
- confounded with a covariate that already encodes the same information (e.g. day-of-week standing in for a promo calendar the org actually has)
