# Reproducibility discipline

"If it can't be reproduced, it didn't happen." (axiom 5) Concretely:

## Seeds

- Set a seed for every stochastic operation: `train_test_split`, model constructors with randomness, `np.random`/`random`/`torch` global state, sampling, shuffling.
- Set it once, near the top, and pass it explicitly rather than relying on a global default that might drift between library versions.
- A result that changes on rerun without a stated reason (new data arrived, intentional re-tune) is not a result yet.

## Data versioning

- Reference the exact snapshot/version/date-range the analysis used — a filename, a table's `as_of` partition, a commit hash of a data export, a query's exact WHERE clause with dates. "The customers table" is not a version; "customers as of 2026-06-30 snapshot" is.
- If the underlying table is mutable (not append-only), note that a rerun today may not match — that's a caveat to state, not a reason to skip versioning.

## Environment

- Pin dependency versions (`requirements.txt`/`pyproject.toml`/lockfile), not just names.
- Note the language/runtime version if it plausibly matters (numeric libraries occasionally change default behavior across major versions).

## Rerun path

- One command reruns the whole analysis end to end: a script, a notebook with a documented run-all order, or a pipeline entrypoint. If reproducing it requires remembering an undocumented manual step, it's not reproducible yet — document the step or automate it.
- Notebooks: cells must run top-to-bottom in order without hidden state from out-of-order execution. See `notebook-hygiene` skill for the maturity ladder toward a script/pipeline.

## What "reproducible" does not mean

It doesn't mean bit-identical forever regardless of library upgrades — it means: given the stated seed, data version, and environment, a rerun produces the same conclusion. State the boundary of that guarantee rather than overclaiming it.
