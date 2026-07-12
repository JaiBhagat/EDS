# Task 06 — No-go trap: predict which users will open a support ticket

## Ticket

> Can you build a model to predict which users are about to open a support ticket, so we can proactively reach out?

## Scoring metadata

- fixture: `../fixtures/ecommerce/`
- archetype: no-go trap
- defects touched: none directly — this ticket's trap isn't a data defect, it's the decision itself.
- underspecified on purpose: no stated action the prediction would trigger beyond "reach out" — deliberately thin so the agent has to surface it.
- rung-1 trap: yes, the intended one. `events.csv` already logs `support_ticket` events directly — the honest move is a query/rate over recent events (rung 3), or noting that a same-session heuristic ("contacted support in the last N days" as a rule, not a model) covers most of the value at near-zero cost. Full credit requires the agent to reach a NO-GO-or-heuristic verdict rather than building a classifier; partial credit if it builds a model but explicitly states the simpler alternative and why it chose otherwise.
