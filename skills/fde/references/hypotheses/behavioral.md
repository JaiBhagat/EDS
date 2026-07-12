# Behavioral

**Claim pattern:** past occurrence/frequency of behavior X predicts outcome Y, because it reveals persistent intent or habit rather than a one-off.

**Precondition probe:** entity has ≥N historical events of type X available before the decision point; the event table actually links to the entity key (check join hit-rate, don't assume it).

**Construction recipe:** count or boolean flag of behavior X within the window available at decision time.

**Canonical failure modes:**
- behavior too rare in the population to generalize past the sample it was observed in
- behavior is itself a proxy for the label (circularity) — run it through leakage-check before trusting a strong score
- behavior window drawn using data only available after the decision point
