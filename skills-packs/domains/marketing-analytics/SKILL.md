---
name: marketing-analytics
description: >
  Domain pack for marketing measurement — MMM, attribution, incrementality,
  CAC/LTV, media saturation. Vocabulary map and canonical metrics/pitfalls
  only — extends core skills, never restates them. Not installed by
  default.
license: MIT
---

# Marketing analytics (domain pack)

Deliberately thin, per the extension convention: vocabulary + canonical metrics + never-cut extensions. Everything else is already core.

## Vocabulary map

MMM (marketing mix modeling) → a regression/Bayesian model of channel contribution to an outcome, evaluated the same way any model is (`evaluation-design`). Attribution → assigning credit for a conversion across touchpoints; a modeling choice, not ground truth, state the model. Incrementality → the causal-inference question ("did this spend cause this outcome") underneath most MMM/attribution claims. CAC/LTV → cost-to-acquire vs. lifetime value, always paired, never quoted alone. Media saturation curves → diminishing-returns response functions per channel, the thing an MMM is usually built to estimate.

## Canonical metrics

Incremental ROAS (not raw ROAS — raw ROAS conflates correlation with causation); adjusted CAC (blended CAC hides channel-level truth); LTV:CAC ratio with a stated time horizon (LTV without a horizon is a guess dressed as a number).

## Never-cut extensions

1. **A geo-holdout or incrementality test is the baseline burden of proof for any MMM claim**, not the MMM's own fit statistics — extends `baseline-first` + `evaluation-design`: an MMM that explains its own training data well is not evidence of incrementality, that's what the holdout test is for.
2. **Seasonality/promo-calendar confounding is a canonical leakage-adjacent pitfall** — a channel's spend often correlates with a promo calendar the model doesn't see, inflating its apparent contribution. Extends `leakage-check`'s temporal awareness and ties directly to `fde`'s `temporal`/`seasonality` hypothesis families — check for this confound before trusting a channel-contribution number.

## Governance

No extension to `model-governance` by default — marketing measurement is rarely a regulated decision. If a specific use becomes one (e.g. a pricing decision with disclosure requirements), that governance need is domain-specific to *that* decision, not this pack.
