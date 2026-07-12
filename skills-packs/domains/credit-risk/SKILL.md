---
name: credit-risk
description: >
  Domain pack for credit risk scoring — PD/LGD/EAD, WOE/IV, adverse
  action, vintage analysis, roll-rate. Vocabulary map, canonical metrics,
  and extensions to model-governance for regulated lending decisions.
  Extends core skills, never restates them. Not installed by default.
license: MIT
---

# Credit risk (domain pack)

Deliberately thin, per the extension convention: vocabulary + canonical metrics + governance/fde extensions. Everything else is already core.

## Vocabulary map

PD/LGD/EAD → probability of default, loss given default, exposure at default — the three components of expected loss; a "risk score" that doesn't map to one of these is underspecified. WOE/IV → weight of evidence / information value, the standard scorecard-building encoding and univariate-screening pair. Adverse action → the regulatory requirement that a rejected applicant receive a specific, reason-coded explanation, not a bare score. Vintage analysis / roll-rate → cohort-based default-timing analysis (this is `label-design`'s maturity-window discipline, applied to credit specifically — a loan's default label isn't mature until its vintage has aged enough to observe it).

## Canonical metrics

KS statistic and Gini/AUC on the scorecard (paired, not either alone); Population Stability Index (PSI) between scoring-time and training-time score distributions — this is `fde`'s stage-7 stability check and `model-monitoring`'s drift check, under its domain name here.

## fde extension

Boosts `aggregation`/`ratio`/`trend` hypothesis family priority (utilization ratios, trailing-aggregate behaviors, and multi-period trend are where credit signal concentrates) with IV emphasis at stage 4's univariate screen. Adds no new funnel stage — stage 8's business explainability review is where WOE-bucket interpretability actually gets checked.

## Governance extension (`model-governance`)

**Adverse-action explainability is mandatory, not optional,** on top of the standard validation package: a rejected applicant's explanation must be reason-coded back to specific, named features — derived from `fde`'s catalog rationale for each feature, not a generic SHAP dump that doesn't map to a disclosable reason. **Disparate-impact / fair-lending review is a never-cut item in this domain**, checked as a mandatory segment slice in `evaluation-design`'s segment-stability check, not an optional one.
