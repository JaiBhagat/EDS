# Anomaly

**Claim pattern:** deviation from the entity's *own* historical baseline predicts outcome better than the raw level — a self-relative signal.

**Precondition probe:** the entity has a stable-enough baseline history to define "normal" (this family needs an explicit cold-start fallback for new entities, stated up front, not discovered later); the baseline window is available at decision time.

**Construction recipe:** `(current value - entity's own rolling mean) / entity's own rolling std`, or a robust z-score variant.

**Canonical failure modes:**
- cold-start entities get an undefined/zero baseline silently treated as "no anomaly" when it should read as "unknown"
- a single early outlier permanently distorts the rolling baseline for everything after it
