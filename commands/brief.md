---
description: Show, edit, or re-confirm the current Problem Brief (.eds/BRIEF.md).
argument-hint: "[show|edit|reconfirm]"
---

# /brief

- No argument or `show`: print `.eds/BRIEF.md` if it exists; if not, say so and suggest `/discover`.
- `edit`: ask which section changed, update it, bump `version`, and re-run the re-confirmation pass on the affected sections only (per `skills/discovery/references/brief-schema.md`'s gating rules) — not a full Discovery re-run.
- `reconfirm`: re-read the Brief aloud in decision language and ask the user to confirm it's still accurate before any downstream skill relies on it.

Never silently modify a confirmed Brief — every edit gets a version bump and an explicit re-confirmation of what changed.
