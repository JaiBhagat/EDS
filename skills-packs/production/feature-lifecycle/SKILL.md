---
name: feature-lifecycle
description: >
  Production pack for feature ownership, lineage, and reuse-before-rebuild
  once a feature set from an FDE campaign is actually shipping — freshness
  SLAs, online/offline parity, training-serving skew. For teams SHIPPING
  models, not analysts answering a question. Not installed by default.
license: MIT
---

# Feature lifecycle (production pack)

## Ladder position

Only relevant once `fde`'s selected feature set is heading to production, not during exploration or a one-off analysis. Most sessions never reach here, and the ladder says some never should (a report or a one-off model doesn't need a lifecycle).

## Owns

Feature ownership, lineage, reuse-before-rebuild, freshness SLAs, online/offline parity, training-serving skew.

## Checklist

1. **Owner + freshness SLA stated per feature.** Every `feature_catalog.json` entry heading to production needs a named owner and a stated freshness SLA (how stale can this feature be before it's wrong) — a feature with neither is not ready to ship, whatever its funnel evidence says.
2. **Reuse before rebuild.** Before engineering a new feature, check the org-scoped catalog (`~/.eds/knowledge/org-feature-catalog.json` when populated) for an existing equivalent — the best new feature is often an existing one (F2's cousin: `fde` §4b).
3. **Online/offline parity check.** Replay the serving-path computation against the training-path computation on a held sample and diff — a feature computed differently at serving time than at training time is a silent, delayed bug, not a one-time check-the-box item.
4. **Training-serving skew monitoring.** Compare the feature's distribution at serving time against its training-time distribution on a rolling basis; drift here is an early warning `model-monitoring` should also be watching for, from the other direction.

## Extends

`fde` (§4b) — consumes `feature_catalog.json` as its contract. This pack does not change catalog schema or funnel stages; it adds a lifecycle status past stage 10 (`selected` → `in production` → `deprecated`), never a new evaluation gate.
