---
name: ds-reporting
description: >
  Translates analysis into decision language for a stakeholder audience —
  answer first, then confidence, caveats, recommendation, in that order. Use
  whenever someone asks to "write this up", "present these results",
  prepare a stakeholder-facing summary, or turn a notebook's output into
  something a non-technical reader acts on. Do NOT use for the analysis
  itself — hand off to `eda-workflow` or `eds-core` to produce the results
  first; this skill only governs how finished results get communicated,
  not how they're produced.
argument-hint: "[audience]"
license: MIT
---

# DS reporting

`EDS.md`'s Tone section, operationalized as a document structure. The failure mode this skill exists to stop: a report that leads with methodology and buries the answer on page 3, or states a metric with no denominator and no caveat, forcing the reader to do the "so what" work themselves.

## The order, always

1. **Answer.** The direct answer to the decision in view, in the first sentence or line. Not "we analyzed X" — the actual finding.
2. **Confidence.** How sure, and based on what (sample size, holdout type, how many comparisons). A number with no denominator is not a finding, it's a fragment — "12% lift" means nothing without "on what base, over what period, measured how."
3. **Caveats.** What could make this wrong or not generalize (a segment it doesn't hold for, a time window it was measured over, an assumption baked into the label or metric). State them plainly, don't bury them in a methodology appendix where they won't be read before a decision is made.
4. **Recommendation.** What to actually do, tied to the decision the analysis served (per axiom 1 — if there's no recommendation, question whether the analysis needed to exist).

## Computed intervals, not asserted ranges

Any headline metric computed on fewer than ~500 positives MUST carry a computed bootstrap interval — never assert a range. Run:

    python scripts/lib/bootstrap_ci.py <predictions.csv> \
        --y-true <col> --y-prob <col> --metric <metric>

Report the interval, not just the point estimate. A report that says "AUC is 0.82" when the 90% bootstrap CI is [0.74, 0.88] is misleading — report both.

## Numbers carry denominators

Every rate, lift, or count in the report states what it's a fraction/change of. "Reduced churn by 15%" is incomplete; "reduced churn from 8% to 6.8% of the at-risk segment (n=12,400), measured over the 90-day holdout" is a finding a reader can act on and a skeptic can check.

## Uncertainty in plain language

State it the way the audience can use it, not just as a p-value or CI in isolation: "this could plausibly be anywhere from a 5% to 25% improvement — treat the 15% headline as a midpoint, not a guarantee" reads very differently from "p<0.05" to a non-technical stakeholder, and is more honest about what the number actually supports.

## No essays defending a shortcut

If a simplification needs a paragraph to justify, that's `EDS.md`'s own rule: it probably needed the next rung instead, and the fix belongs in the analysis, not in a longer explanation. A report defending its own shortcuts at length is a sign to go back and shore up the analysis, not to write more prose around it.

## Output shape

```
## <decision this serves>
**Answer:** <one line>
**Confidence:** <n, split type, comparisons if relevant>
**Caveats:** <bulleted, plain language>
**Recommendation:** <specific action, or explicit "no action" with why>
```

If the audience is executive/non-technical, this is the entire report — methodology, code, and full metric tables go in an appendix or linked notebook, not the body.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
