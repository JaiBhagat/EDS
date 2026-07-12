# Aggregation

**Claim pattern:** an entity-level summary (mean/sum/max/std) over its own transaction history predicts outcome better than any single transaction does.

**Precondition probe:** entity has enough child rows for the aggregate to be stable, not a summary of one or two points.

**Construction recipe:** group-by-entity aggregate over a window available at decision time — never over the whole table.

**Canonical failure modes:**
- aggregate computed over the *entire* table including future rows — the classic non-time-windowed leak, and the single most common FDE mistake
- aggregate hides a bimodal distribution that a percentile or count would have revealed instead
