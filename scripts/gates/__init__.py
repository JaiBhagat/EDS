"""EDS verification gates — shared infrastructure.

Each gate script validates a stage's Definition of Done, writes a pass/fail
record to .eds/verification/<stage>-<ts>.json, and exits 0 (pass) or 1 (fail).
"""
