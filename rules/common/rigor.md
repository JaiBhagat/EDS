# Rigor — the never-cut list as imperatives

These six are never on the chopping block, at any mode, at any rung of the ladder. If you find yourself justifying why one doesn't apply "this time," that justification is the bug.

1. **Validate the data before you use it.** Assert the grain. Check nulls, duplicates, and ranges against what's plausible. Check join cardinality before trusting post-join row counts.

2. **Prove there's no leakage before you trust a result.** Trace every feature's derivation — could it only exist after the outcome? Check splits for entity overlap. Check that every feature would actually be available at decision time, not just in the historical table.

3. **Evaluate honestly.** Hold out data the model never touched, ideally out-of-time. Pick the metric that matches the decision's cost asymmetry, not the one that looks best. Always compare to a stated baseline — a metric in isolation proves nothing.

4. **State uncertainty, don't hide it.** Say the sample size. Give an interval where the decision is sensitive to it. If you ran more than one comparison, say so and correct for it. Never round "not significant" up to "probably true."

5. **Make it reproducible.** Fix seeds. Reference the data version/snapshot used. Pin the environment. Leave one command that reruns the whole thing — if you can't rerun it, you can't defend it.

6. **Never leak privacy.** No PII in outputs, notebooks, logs, or error messages. Respect aggregation thresholds — a group small enough to re-identify one person is not an aggregate.

## How this interacts with the ladder

The ladder governs how much you build. This list governs what you never skip regardless of how little you build. A one-line group-by still needs the grain check if a decision rides on it. A rung-8 custom pipeline still needs all six, in full.

Deliberately skipping one of these for a stated reason is different from silently omitting it — mark the skip: `# eds: deferred — <reason>`.
