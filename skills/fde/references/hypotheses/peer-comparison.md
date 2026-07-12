# Peer-comparison

**Claim pattern:** an entity's value relative to its cohort (percentile/z-score within peer group) predicts outcome better than its absolute value.

**Precondition probe:** the cohort definition is stated and stable — not silently redefined per row; the cohort has enough members for a percentile to mean anything.

**Construction recipe:** percentile rank or z-score of the entity's value within its cohort, computed using only cohort members' data available at decision time.

**Canonical failure modes:**
- cohort computed using the full dataset, including future entities/rows — a population-level leak
- cohort too small, so the percentile is noisy and shifts every time the cohort refreshes
