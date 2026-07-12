---
name: causal-inference
description: >
  Method pack for effect-estimation questions — "did X cause Y", "what
  happens if we change Z" — where a predictive model's accuracy, however
  high, doesn't answer the question being asked. Reach for this when the
  decision needs an effect estimate, not a prediction. Not installed by
  default — this is an optional pack, not core.
license: MIT
---

# Causal inference (method pack)

## Ladder position

A different question class, not a higher rung of the same one. If the actual ask is "will this specific case do X" (prediction), stay on the standard ladder. If the ask is "did doing X change the outcome, and by how much" (effect estimation), the standard predictive ladder's rungs 6–8 are the wrong tool regardless of how well they'd score — a highly predictive model can still give a badly biased treatment effect.

## Canonical pitfalls

1. **Identification skipped, estimation started immediately.** State the causal question, the treatment, the outcome, and the assumed confounders (a DAG sketch, even a rough one) *before* picking a regression/matching/IV method. A method chosen before identification is a solution to an unstated problem.
2. **Prediction accuracy mistaken for causal validity.** A model can predict the outcome well on held-out data and still produce a badly biased effect estimate — these are different properties, and a good R²/AUC is not evidence the causal claim is right.
3. **Selection bias / non-random treatment assignment ignored.** Who got treated is rarely random in observational data; state the assignment mechanism and what confounds it before estimating.
4. **Overlap (positivity) violated.** If no untreated units resemble some treated units (or vice versa), the estimate for that region is extrapolation, not identification — check covariate overlap before trusting the estimate across the whole population.
5. **Multiple candidate "causal" analyses run, one reported.** Running many specifications and reporting the significant one is p-hacking with extra steps; pre-register the specification or report all of them.

## Library pointers

`DoWhy` for explicit identification (states assumptions, runs a refutation suite) paired with `EconML` for flexible heterogeneous-effect estimation; `statsmodels` for basic IV/difference-in-differences; `causalml` if the actual need is uplift/targeting (a decision-optimization problem wearing a causal-inference hat — check `decision-optimization` first).

## Extends

- `evaluation-design` — causal estimates need placebo tests and sensitivity/refutation analysis, not a train/test split; this pack states what "validation" means for this question class.
- `decision-optimization` — an effect estimate exists to inform an intervention decision; the EV framing there applies once the effect is identified.
