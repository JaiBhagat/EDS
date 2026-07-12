# Causal / measurement archetype bank

For "did X cause Y", "is the new thing worth it", "why did the metric move" problems. Ask after the universal bank, pruned by its answers.

1. **Claim** — What's the exact causal claim ("launching X increased Y")? Restate it so it's falsifiable, not just directional.
2. **Comparison** — What's being compared to what — before/after, treatment/control, this segment/that segment? Is there a valid counterfactual, or does one need to be constructed?
3. **Assignment mechanism** — Was treatment randomized, or did users/entities self-select into it? Self-selection is a confounding flag — surface it now, not after the estimate is produced.
4. **Confounders** — What else changed at the same time as the thing being measured (seasonality, a concurrent launch, a macro shift)? Ask the user what they know; a probe can't reveal what wasn't recorded.
5. **Unit of randomization/analysis** — If experimental: what's the randomization unit (user, session, account)? Does it match the analysis unit? A mismatch inflates false confidence.
6. **Effect size that matters** — What size of effect would actually change the decision? A statistically significant but practically trivial effect is not the same as a decision-relevant one.
7. **Prior evidence** — Has this or something similar been measured before? What did it show?
8. **Timeframe** — Over what window was/will the effect be measured? Long enough to capture novelty-effect decay?
9. **Multiple comparisons** — Is this one clean question, or one of several metrics/segments being checked? Ask explicitly — this determines whether a correction is needed.

## Routing

- Q3–Q5 feed `stats-skeptic` directly — flag confounding/unit-mismatch risks in the Brief even before analysis starts.
- Q2/Q3 determine whether this is `experiment-design` (a true experiment) or an observational causal question needing an identification strategy (DAG-lite, methods pack) — route accordingly, don't default to a simple before/after.
- Q6 becomes the pre-registered effect-size floor in the success-metric section of the Brief — capture the number, not just "significant."
- Q9 answer, if "several", triggers a stated multiple-comparison correction in `evaluation-design` — never silently skip it.
