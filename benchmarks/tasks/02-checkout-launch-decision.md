# Task 02 — Is the new checkout worth launching?

## Ticket

> We ran the new checkout flow for a subset of users. Orders data has both flows mixed in (there's no explicit A/B flag in this fixture — assume `region` in `["north","south"]` saw the new flow, `["east","west"]` saw the old one, if you need a stand-in split for this ticket). Is the new checkout worth launching to everyone?

## Scoring metadata

- fixture: `../fixtures/ecommerce/`
- archetype: measurement / experiment read-out
- defects touched: none of the 5 core defects directly — this ticket tests experiment-design instincts (confounding, sample-size adequacy, effect size vs. significance) rather than the planted data defects.
- underspecified on purpose: no stated decision cost, no randomization guarantee stated (the "assume region proxies for arm" instruction is a confound the agent should flag, not accept quietly) — tests whether stats-skeptic-style reasoning fires even without the `stats-skeptic` agent being explicitly invoked.
- rung-1 trap: partial — a correct answer may be "this comparison is confounded by region, we can't answer the launch question from this data as given," which is a form of no-go.
