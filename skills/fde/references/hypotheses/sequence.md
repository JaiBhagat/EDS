# Sequence

**Claim pattern:** the *order* events happened in — not just their count — predicts outcome (an escalation pattern, action-then-action).

**Precondition probe:** the event table has reliable ordering (timestamp precision finer than the pattern being tested); enough entities exhibit the candidate sequence to evaluate it at all.

**Construction recipe:** n-gram/transition flags over the entity's ordered event history up to the decision point.

**Canonical failure modes:**
- timestamp ties silently break the claimed order
- the sequence pattern is rare enough that any measured lift is noise — check support before evaluating, not after a surprising score
