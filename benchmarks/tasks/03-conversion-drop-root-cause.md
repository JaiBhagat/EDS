# Task 03 — Why did conversion drop?

## Ticket

> Someone on the team mentioned conversion looked worse recently. Can you look into why?

## Scoring metadata

- fixture: `../fixtures/ecommerce/`
- archetype: descriptive / root-cause
- defects touched: 1 (duplicated rows — a naive conversion-rate calc that doesn't dedup `orders` first will be off).
- underspecified on purpose: deliberately vague — no time window, no metric definition, no "recently" anchor, no numbers at all. This is the benchmark's clearest discovery-quality test: does the agent ask a small number of sharp questions (what's the conversion metric, over what window, compared to what baseline period) before writing any code, or does it guess a definition and start querying immediately.
- rung-1 trap: yes — the correct rung is very likely 3 (a group-by/crosstab over time), not a model. An agent reaching for ML here is a clear over-build catch.
