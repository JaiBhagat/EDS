---
description: Start or resume the Discovery Loop to produce/update .eds/BRIEF.md.
argument-hint: "[resume|restart]"
---

# /discover

Invoke the `discovery` skill.

- No argument, or `resume`: if `.eds/BRIEF.md` exists with `status: draft`, continue from the last completed stage. Otherwise start at Stage 0.
- `restart`: confirm with the user before discarding an existing Brief, then start fresh at Stage 0.

Follow `skills/discovery/SKILL.md` exactly — gated stages, batched questions (2–4 per turn), probes before user questions wherever a probe can answer it, no proceeding past a stage without its exit condition met.
