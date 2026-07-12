---
name: label-design
description: >
  Designs how the target/label is constructed before anything is trained on
  it — a specialization of axiom 4 (time flows one way) applied to the
  label itself rather than the features. Handles delayed/censored labels,
  proxy or weak labels, label lag vs. decision cadence mismatches, and gold-
  set construction. Use this whenever a label isn't simply "already
  observed and final" at training time: outcomes that mature over days/
  weeks (churn, default, fraud chargeback), proxies standing in for a true
  target that's expensive or impossible to observe directly (using "clicked"
  as a proxy for "satisfied"), or any target requiring a hand-labeled gold
  set. Do NOT use when the label is a simple, immediately-final, directly-
  observed field (e.g. transaction amount already recorded) — go straight
  to `data-audit`/`leakage-check` instead.
argument-hint: "[label-definition|maturity-window]"
license: MIT
---

# Label design

If `.eds/BRIEF.md` exists, its "Target & label strategy" section already states the label definition, delay/censoring, and proxy-bias notes discovery surfaced — verify those against the actual data here, don't re-derive them from a blank page.

## The four checks, in order

### 1. Maturity window vs. training cutoff

If the label needs time to resolve (a loan defaults within 90 days, a customer churns within a quarter, a fraud case charges back within 45 days), every row in the training set must have had its *full* maturity window elapse before the label is treated as final. A row observed 10 days ago in a 90-day-maturity label is not "label = 0 (no default yet)" — it's "label unknown, censored." Silently coding censored-as-negative systematically biases the target toward the majority class and undercounts the event you're trying to predict. Run `skills/label-design/scripts/label_maturity.py <path.csv> --event-date-col <col> --observed-until <date> --maturity-days <n>` to flag rows that haven't cleared the window.

### 2. Label lag vs. decision cadence

Separately from label maturity: how long after an event does the *true* label even become knowable in the source system (a chargeback might not be flagged in the data for another week after the 45-day maturity ends)? If that lag is longer than the decision cadence stated in the Brief (e.g. deciding daily but labels lag by weeks), the model will always be trained on stale ground truth relative to what it's deciding on — state this gap explicitly, it changes what recency of data can honestly back a "current" model.

### 3. Proxy/weak label bias

If the true target isn't directly observable and a proxy stands in for it (clicks for satisfaction, self-reported for actual, a rule-based label for a not-yet-labeled outcome), name the proxy's failure mode explicitly: who does the proxy systematically mis-represent, and in which direction? A proxy that's biased in a known direction isn't disqualifying — training on it while pretending it's the true target is. Document it in the same place the label is defined, not as a footnote.

### 4. Gold-set construction (when proxy/weak labels are used)

If a small hand-labeled gold set is used to estimate proxy bias or calibrate against, check: is it a random sample of the population the model will actually score, or a convenience sample (easy cases, recent cases, cases someone happened to review)? A gold set that isn't representative can't correct the bias it's meant to measure — it just launders it with a smaller number.

## Output

```
## Label design: <target>
- maturity: <window>, <n> rows censored/excluded
- lag vs. cadence: <finding>
- proxy bias: <direction/who's misrepresented, or "true label, N/A">
- gold set: <representative/convenience, n>
```

If maturity can't be verified (no event-date column, no stated cutoff), that's a finding, not a silent pass: `# eds: deferred — cannot verify label maturity, no event-date column on <table>`.

## Handoff contract

On completing this stage: (1) mark the Plan entry for this stage `done` with the gate-record reference, (2) read the Plan in `.eds/BRIEF.md`, (3) **state the next pending stage and proceed into it** — unless that stage carries a `user-signoff` gate, in which case present the decision and stop. Never end a turn with a generic "what next?" while the Plan has a pending ungated stage.
