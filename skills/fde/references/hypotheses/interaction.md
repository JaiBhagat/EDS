# Interaction

**Claim pattern:** signal is conditional — feature A only matters in the presence/context of feature B, a state univariate screening will miss.

**Precondition probe:** both interacting features individually pass availability and non-degenerate checks; the conditioning has a stated business reason, not a blind pairwise sweep.

**Construction recipe:** an explicit product/conditional-encoding term, or a per-segment version of an existing feature.

**Canonical failure modes:**
- the interaction is really a proxy for a segment identifier the model would rather see directly
- generating all pairs instead of theorized ones — stage 4's univariate screen correctly won't kill these (F1 exists precisely so this isn't a license to skip having a hypothesis)
