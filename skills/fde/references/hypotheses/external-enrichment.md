# External-enrichment

**Claim pattern:** data the org has access to but hasn't joined in yet (third-party enrichment, another system's table) would carry signal.

**Precondition probe:** this is a **user question, not a data probe** — confirm the data actually exists, is licensed/available, and can be obtained point-in-time, before instantiating anything.

**Construction recipe:** none until confirmed. Until then this family produces a Discovery Stage 3 gap-list entry, not a feature.

**Canonical failure modes:**
- engineering a feature against a one-off sample/export of external data that won't be refreshable in production — passes the funnel, fails stage 9 (serving review)
- treating "we could enrich with X" as already-done when it's still hypothetical
