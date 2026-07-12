---
description: Start or resume an FDE feature-discovery campaign.
argument-hint: "[target|resume|status]"
---

# /features

Invoke the `fde` skill.

- No argument, or a target name: start a new round against `.eds/features/feature_catalog.json` (creating it if absent) for the stated target. Require `data-audit` and a confirmed `.eds/BRIEF.md` first — hand off if either is missing.
- `resume`: continue the current campaign from `.eds/features/candidate_features.md` if a round is in progress, otherwise start the next round.
- `status`: report campaign state without running a new round — cataloged/selected/rejected counts, rounds run, last stopping check, from `feature_catalog.json` and the journal's last stop-decision entry (grep, don't bulk-load the journal).

Follow `skills/fde/SKILL.md` exactly — hypothesis before feature, the staged funnel in order, the confirmation holdout touched once per campaign. For a small campaign (a dozen candidates) run inline; for a full campaign (hundreds-to-thousands) delegate to the `feature-scientist` agent and return only round summaries.
