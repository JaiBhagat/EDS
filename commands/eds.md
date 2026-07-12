---
description: Switch or show the EDS mode (lite, full, ultra, off).
argument-hint: "[lite|full|ultra|off]"
---

# /eds

Show or set the EDS mode.

- No argument: report the current mode (from `EDS_DEFAULT_MODE` env var, `~/.config/eds/config.json`, or the session default `full`) and give a one-line reminder of what that mode enforces.
- `lite`: ladder advice only, never blocks, never-cut items become warnings.
- `full` (default): ladder enforced in reasoning, never-cut items are hard requirements, deferred markers required for skips.
- `ultra`: audit posture on every touch, reviewer agents auto-invoked on model-related diffs.
- `off`: plugin stays silent; skills remain invocable manually.

Apply the mode for the rest of this session immediately after switching — don't wait for the next message. Confirm the switch in one line, per `EDS.md`'s tone rules.
