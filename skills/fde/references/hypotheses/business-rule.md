# Business-rule

**Claim pattern:** a heuristic analysts already use informally (e.g. "three failed payments in a week is a red flag") carries signal because domain experts already rely on it.

**Precondition probe:** the rule is stated precisely enough to implement — ask the user for the exact threshold/window, don't guess one; the event data needed to compute it exists and is available at decision time.

**Construction recipe:** direct implementation of the stated rule as a boolean/count feature — no embellishment beyond what was stated.

**Canonical failure modes:**
- the informally-described rule has an ambiguous threshold that gets guessed instead of confirmed with the domain owner
- the rule was originally described using information analysts only had in hindsight, not available at the actual decision point
