# Communication — decision-first, not metric-first

Analysis serves a decision (axiom 1). Write it up so the decision-maker can act without decoding a metric first.

## Structure every result in this order

1. **Answer** — the direct response to the question asked, in plain language.
2. **Confidence** — how sure, and why (sample size, interval, out-of-sample check).
3. **Caveats** — what would change the answer, what wasn't tested, known limitations.
4. **Recommendation** — the action implied, if any. If the honest answer is "don't act on this yet," say that.

Don't bury the answer at the end of a methods walkthrough. Lead with it.

## Numbers carry denominators

"Conversion up 12%" is not a number, it's a fragment. "Conversion up 12% (1,240 → 1,389 of 11,300 sessions)" is. A rate, a lift, or a share without its base invites misreading — always state what it's a percentage *of*.

## Uncertainty in plain language

- Prefer "this is based on 340 events, so the estimate could reasonably be anywhere from X to Y" over a bare p-value.
- Say when a result is directionally suggestive but underpowered, rather than dressing it up as confirmed.
- If multiple metrics/segments were checked, say how many, and whether the standout survived correction — don't let the reader assume one clean test.

## No essays defending a shortcut

If an explanation of a simplification runs longer than the simplification itself, that's a sign the next rung of the ladder was needed, not a longer justification. State what was skipped and when to revisit it, in one line, and move on (see `EDS.md`'s tone rules and the deferred-work marker convention).

## Audience calibration

A stakeholder-facing readout and an internal handoff to another data scientist carry different detail levels — but never at the cost of the never-cut list. A stakeholder doesn't need the leakage-scan methodology; they do need to know the result was checked for it. An internal handoff needs both.
