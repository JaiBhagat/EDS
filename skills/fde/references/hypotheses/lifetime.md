# Lifetime

**Claim pattern:** tenure or lifecycle stage (new/established/dormant) predicts outcome independent of recent activity.

**Precondition probe:** an entity creation/first-seen timestamp exists and is reliable — not backfilled inconsistently across a migration.

**Construction recipe:** days/periods since first-seen at decision time, or an explicit lifecycle-stage bucket.

**Canonical failure modes:**
- first-seen timestamp itself was backfilled inconsistently across a system change, creating an artificial step in the feature that has nothing to do with the entity
- lifecycle bucket boundaries chosen post-hoc to fit the current data rather than a stated business definition
