# Prediction archetype bank

For per-entity outcome problems: churn, fraud, default, conversion, upsell, attrition. Ask after the universal bank, pruned by its answers.

1. **Label definition** — How exactly is a positive defined today (a column, a rule, an analyst call)? Has that definition changed over time?
2. **Label timing** — How long after the decision point is the outcome known? Is there a maturity/censoring window (e.g. "default within 90 days")?
3. **Label quality** — Are labels ground truth, a proxy, or weak/noisy? Any known mislabeling sources (e.g. "churn" = cancelled vs. went quiet)?
4. **Typical signal** — State what problems of this shape typically use (tenure, engagement recency, contact history, billing events, etc. — tailor to the stated domain) and ask which of these exist, even messy, and which don't. This is the gap-analysis move: experience-driven, not a blank "what data do you have."
5. **Decision-time availability** — At the moment this prediction is made, what information is actually available? (Anything computed after the decision point is a leakage risk, not a feature.)
6. **Action per score band** — Is there a defined action for high/medium/low scores, or does the model just inform a discussion?
7. **Capacity** — If this feeds a review queue or intervention list, what's the team's capacity? A model tuned for recall that triples the queue is a failure (A6).
8. **Population stability** — Does the entity population change over time (new customer segments, new products) that the training data might not reflect?
9. **Existing heuristic** — Is there a current rule-of-thumb humans use for this ("accounts inactive >60 days are at risk")? That's rung 5 — get it stated precisely, it may already meet the bar.

## Routing

- Delayed/proxy/weak label answers (Q1–Q3) → route to `label-design` skill for Stage 5 framing, don't resolve inline.
- Q6/Q7 answers feed `decision-optimization` later — capture verbatim, don't pre-solve the threshold here.
- Q4 answers become the seed of the FDE's first hypothesis round — capture as have/missing/proxy, not prose.
