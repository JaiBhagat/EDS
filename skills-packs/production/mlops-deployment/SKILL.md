---
name: mlops-deployment
description: >
  Production pack for shipping a model to serve live traffic — experiment
  tracking, model registry, CI/CD for models, shadow deployment,
  champion-challenger, canary rollout, rollback criteria, batch vs.
  streaming serving topology. Reasoning and design patterns, not tooling
  — does not replace a registry or CI system. Not installed by default.
license: MIT
---

# MLOps deployment (production pack)

## Ladder position

Only relevant when a model is actually being shipped to serve live traffic, not for an offline analysis or a one-off report — most sessions never reach here, and that's correct, not a gap. This pack teaches deployment *reasoning*; it does not replace a model registry, a CI system, or an orchestration platform, and core never depends on it (an analyst's notebook question must never require production concepts to answer).

## Owns

Experiment tracking, model registry, CI/CD for models, shadow deployment, champion-challenger, canary rollout, rollback criteria, batch vs. streaming serving topology.

## Checklist

1. **Shadow before cutover.** Run the new model alongside the current one on live traffic without acting on its output first — compare their decisions before either the metric or the business impact changes.
2. **Champion-challenger, not a single cutover.** Route a stated fraction of traffic to the challenger; the fraction and the promotion criterion are decided *before* the test starts, not after seeing early results.
3. **Canary rollout with a rollback criterion stated in advance.** "We'll roll back if it looks bad" is not a criterion — state the specific metric, threshold, and sample size that triggers rollback before the canary starts.
4. **Rollback on statistically significant degradation over N requests, not the first bad request.** A single bad prediction is expected variance, not a signal — the rollback trigger needs a stated sample size and significance bar, mirroring `evaluation-design`'s bootstrap-comparison discipline.
5. **Batch vs. streaming topology chosen for the decision's actual latency requirement,** not by default — a batch-scored decision doesn't need a streaming pipeline built for it just because streaming is available.

## Extends

`model-monitoring` — deployment topology decisions (canary, shadow, rollback) are upstream of the ongoing drift/decay monitoring that skill owns once the model is live.
