# Benchmark results

No agentic benchmark run has been completed yet.

`tests/test_fixture_defects.py` provides deterministic proof that the plugin's checks catch all five planted defects (duplicate grain, target leakage, entity-overlapping splits, time-shuffled CV, mismatched metric). This runs in CI on every push with no API key required.

A comparative eds/no-eds run is tracked as:

```
# eds: deferred — proof-of-value benchmark (eds vs no-eds arms), P2b, needs API budget
```
