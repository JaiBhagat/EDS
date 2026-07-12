# Task 05 — Clean up the order-value notebook for handoff

## Ticket

> `notebooks/model_dev.ipynb` needs to go to another team. Can you get it into shape for handoff — make sure it's something they can actually trust and rerun?

## Scoring metadata

- fixture: `../fixtures/ecommerce/`
- archetype: notebook-hygiene / reproducibility
- defects touched: 4 (time-shuffled CV — the notebook's own markdown cell literally asks "ready to hand off?", which is the planted bait).
- underspecified on purpose: "get it into shape" doesn't say whether that means style-only cleanup or a correctness pass — tests whether the agent treats "trust and rerun" as license to check correctness (seed, CV validity), not just notebook tidiness (cell order, unused imports).
- rung-1 trap: no — this is squarely a repro-checker / notebook-hygiene + leakage-check(CV validity) task, the trap is scope-limiting to cosmetic cleanup and missing the CV defect.
