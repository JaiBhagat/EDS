---
name: data-contracts
description: >
  Production pack for preventing bad data at the source, rather than
  auditing after — schema evolution, source ownership, breaking-change
  detection, contract tests at ingestion. For teams owning an ingestion
  pipeline, not analysts consuming an existing warehouse table (they
  still just use data-audit). Not installed by default.
license: MIT
---

# Data contracts (production pack)

## Ladder position

Only relevant if you own the ingestion pipeline the data comes from. If you're an analyst consuming an existing table, `data-audit` is still the right (and sufficient) tool — this pack is about preventing the problem `data-audit` would otherwise catch downstream, not a replacement for it.

## Owns

Preventing data from going bad, vs. auditing after: schema evolution policy, explicit source ownership, breaking-change detection, contract tests run at ingestion.

## Checklist

1. **A contract per source table:** `{schema, owner, freshness SLA, breaking-change policy}` stated explicitly, not implied by "whoever wrote the pipeline."
2. **Breaking-change detection at ingestion, not three joins downstream.** A schema change (dropped column, changed type, changed grain) fails a contract test at the point of ingestion — the same failure discovered by `data-audit` three joins later is a much more expensive version of the same bug.
3. **Ownership is a name, not a team.** "Data platform team owns this" without a named point of contact means no one owns it when it breaks.
4. **Freshness SLA is testable, not aspirational.** State the check that would actually fail if the SLA were violated (row count in the last N hours, max timestamp lag), not just a documented target.

## Extends

`data-audit` — this pack is the preventive half of the same axiom (A2, the data is guilty until proven innocent); `data-audit` still runs on any table regardless of whether a contract exists, because a contract can itself be violated.
