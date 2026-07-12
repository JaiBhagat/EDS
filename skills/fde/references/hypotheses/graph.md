# Graph

**Claim pattern:** connections between entities (shared device, address, counterparty, referrer) carry signal a single-entity view can't see.

**Precondition probe:** a linkage table exists and actually connects a meaningful fraction of entities (not near-empty); the graph is buildable point-in-time — edges are dated, not a full-history snapshot.

**Construction recipe:** degree/neighbor-aggregate features (count of distinct entities sharing a device, neighbor's own outcome rate) computed only from edges available before the decision point.

**Canonical failure modes:**
- graph built from the full dataset including future edges — a severe temporal leak, and an easy one to miss because it "feels like" a static reference table
- a shared-attribute signal that's really just "everyone at company X," not the relationship the hypothesis claimed — needs the stage-8 business sanity check
