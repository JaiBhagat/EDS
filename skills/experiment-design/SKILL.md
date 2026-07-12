---
name: experiment-design
description: >
  Designs an A/B test or experiment before it launches — sample size/power,
  guardrail metrics, randomization unit, and peeking discipline. Use whenever
  someone proposes an A/B test, wants to size an experiment, asks "how long
  do we need to run this", or is about to make a launch decision from
  experiment results. Also trigger on "can we just check it early" or any
  request to look at results before the pre-registered sample size is
  reached. Do NOT use for observational/non-randomized comparisons — that's
  the `causal-inference` pack, which handles identification without
  randomization.
argument-hint: "[baseline-rate|metric] [mde]"
license: MIT
---

# Experiment design

Axiom 3 (baseline is the burden of proof) and axiom 4 (leakage/contamination discipline) applied to randomized experiments. If `.eds/BRIEF.md` exists, its cost-of-being-wrong and cadence sections inform the MDE and guardrail choices below — don't pick them from scratch.

## The four things to fix before launch

### 1. Randomization unit vs. analysis unit

State the randomization unit explicitly (user, session, device, account) and confirm the analysis unit matches it. Analyzing at a finer grain than randomization (e.g. randomizing by user but analyzing by session) inflates the effective sample size and understates variance — the classic silent power-calc error. If the two units differ, the sample-size math below must use the randomization unit's count, not the analysis unit's.

### 2. Sample size / minimum detectable effect (MDE)

Run `skills/experiment-design/scripts/power_calc.py --baseline <rate-or-mean> --mde <absolute-or-relative> [--metric-type proportion|mean --std <sd>] [--alpha 0.05] [--power 0.8]` — it reports the required sample size per arm for the stated MDE, or (given `--observed-n`) the MDE actually detectable at that sample size. An experiment sized after the fact to "whatever traffic we have" without checking the detectable MDE is a guess dressed as a test — always check which direction the calc is being used for and say so.

### 3. Guardrail metrics

Before launch, name the metrics that must *not* regress even if the primary metric wins (latency, unsubscribe rate, support tickets, a different revenue line). A primary-metric win that trades off a guardrail is not an unconditional ship decision — state the guardrail set and its bar up front, not after seeing results that would otherwise look good in isolation.

### 4. Peeking / sequential-testing discipline

State before launch whether this is a fixed-horizon test (analyzed once, at the pre-registered sample size) or a sequential/always-valid design (needs a correction method — e.g. alpha-spending, mSPRT). Checking a fixed-horizon test's p-value repeatedly and stopping the first time it crosses significance inflates the false-positive rate far above the stated alpha — this is peeking, and it is a hard stop: either commit to the pre-registered horizon, or use a sequential method designed for repeated looks, never both at once.

## Novelty effects

If the experiment measures a UI/behavior change, note that early results can overstate or understate the steady-state effect (novelty or change-aversion). A short experiment on a change with a plausible novelty effect should say so as a caveat, not report the early lift as the durable one.

## Output

```
## Experiment: <name>
- randomization unit: <unit> — analysis unit: <unit, match/mismatch>
- sample size: <n/arm> for MDE <value> at alpha=<a>, power=<p>
- guardrails: <metric>: bar <value>, ...
- analysis plan: fixed-horizon (n=<n>) | sequential (<method>)
```

If any of the four isn't fixed yet, that's a launch blocker, not a detail to fill in later — say so plainly rather than letting the experiment start unsized.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
