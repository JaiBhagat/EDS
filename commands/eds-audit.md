---
description: Run the five-subsystem harness auditor — Brief/Plan, gate records, data manifest, handoff notes, ledgers.
argument-hint: "[project-dir]"
---

# /eds-audit

Run `python scripts/eds_audit.py` to audit the project's EDS harness health.

Five subsystems checked:

1. **Brief + PROJECT.md** — Brief exists, confirmed, Plan section present
2. **Plan gates** — every `done` stage has a passing gate record in `.eds/verification/`
3. **Data manifest** — exists, has sources, all audited within 30 days
4. **Handoff notes** — `progress.md` has a resume/handoff block
5. **Ledgers** — holdout ledger has no duplicate unforced touches; debt ledger tracked

Exits 0 when critical items (plan gates, manifest) pass. Non-critical warnings (missing PROJECT.md, no handoff notes) don't block.

Report the findings in structured form. If any critical subsystem fails, state what's broken and what to fix — don't summarize as "mostly fine."
