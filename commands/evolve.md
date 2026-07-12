---
description: Cluster recurring deferral patterns in the debt ledger into candidate skill/hook improvements.
argument-hint: "[min-count]"
---

# /evolve

Run `scripts/evolve-cluster.js .eds/debt-ledger.md --min-count <n>` (default `n=3`) and report the result.

This is the ECC continuous-learning-v2 pattern applied to `.eds/debt-ledger.md`: the Stop hook (`harvest-debt.js`) already collects every `# eds: deferred` marker across sessions — this command looks for the same reason recurring across entries, which means a one-off shortcut has become a pattern worth fixing at the source (a new `ds-lint.js` check, a new skill section, a new never-cut clarification) rather than re-deferring it every session.

Present each cluster as: the recurring keyword, how many times it's shown up, up to 3 example entries, and a one-line recommendation of where it belongs (hook check vs. skill content vs. a genuinely one-off coincidence not worth acting on — clustering finds candidates, it doesn't force action on all of them). Do not silently "fix" the underlying pattern as part of running this command — report it, let the user decide whether it's worth the change.
