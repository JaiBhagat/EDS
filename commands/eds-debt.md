---
description: Harvest eds:deferred markers from the touched files into the debt ledger.
argument-hint: "[path]"
---

# /eds-debt

Scan the current diff (or the given path, or the whole repo if no diff exists) for `# eds: deferred — <reason>` markers and any `no-brief` deferrals logged during discovery skips.

Append new entries to `.eds/debt-ledger.md` (create it if absent) as a dated list: file:line, the deferred reason, and which never-cut item or ladder rung it relates to. Don't duplicate entries already in the ledger. Report a one-line count of new entries found.

This is the same operation the Stop hook (`hooks/scripts/harvest-debt.js`) performs automatically at session end — this command lets the user run it on demand mid-session.
