# Stage 8 — Business explainability review

| | |
|---|---|
| Cost class | human review — not automatable |
| Applicable task types | all, mandatory in regulated domains |
| Output schema | `{candidate, confirmed: bool}` |
| Implementation | `scripts/evaluators/funnel.py::stage_8_business_explainability` |

**Gate:** can a domain owner say what this feature means and why it should work? This stage does not auto-evict — it separates confirmed from unconfirmed candidates so the campaign can track sign-off status explicitly rather than skip it.

**Why it exists:** unexplainable features are debt in regulated domains and fragile everywhere; feeds the `model-governance` pack when installed.
