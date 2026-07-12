# Frequency

**Claim pattern:** how often something occurs (count/rate) predicts outcome, independent of recency or magnitude.

**Precondition probe:** the count is meaningfully bounded (not dominated by an outlier/bot entity); observation windows are comparable across entities, or exposure-normalizable if not.

**Construction recipe:** count or rate over a fixed available-at-decision window, normalized by exposure time when entities have unequal tenure.

**Canonical failure modes:**
- unequal observation windows across entities without exposure normalization — a longer-lived entity always "has more," which isn't the claimed effect
- the count conflates two distinct underlying behaviors that should be separate features
