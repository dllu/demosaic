# Weak-detail literature review and reconstruction ideas

Recorded: 2026-11-15T23:04:10-08:00 (America/Los_Angeles).

The user requested a progress review, literature search and ideas for recovering
fine low-amplitude detail without splotches or hallucinated texture, explicitly
without implementation. Reviewed PROMPT/AGENTS, current model/experiment/data
docs, V198–V200 outcomes and gate controls, green-phase and known-template
diagnostics, conditional-noise response and earlier loss/matching results.
Actually viewed the existing V200 EMA mesh2302/2309, cab and building triplets.

The [research note](../docs/weak-detail-literature-2026-11.md) records primary
sources from NTIRE2026, AIM2025, structural-guided JDD, NLFeMF, NSP, IDF, PixIE
and the RAW/RGB pipeline benchmark, plus statistical references. Full method
and protocol sections were read where noted; abstract-only readings are labeled.
CVF PDF fetches for NSP/IDF returned403; their arXiv HTML papers supplied the
method reading instead. No external implementation or weights were downloaded.

The central inference is that stronger response alone is insufficient:
selection/support reuse noisy evidence, strong edges may contaminate wave
fits, and loss changes have repeatedly exchanged detail for quiet-field error.
Prioritize the prepared shared-edge data comparison, then truly withheld-sample
evidence and a local edge/background nuisance model. Further hypotheses cover
constrained aggregation, separate coarse/detail optimization, calibration and
training-domain mismatch, and a modern full-model/DINO-role comparison.
The note explains independence leakage through a full-input frozen anchor and
distinguishes empirical support from calibrated confidence.

README and documentation indexes link the note. V120 remains the general
recommendation; shared-edge trained quality remains unmeasured. No code,
recipes, checkpoints, training, inference, new image generation or original-media
access was involved. Historical receipts and image evidence remain unchanged.
The diary helper was run with `.venv/bin/python` because `python` was absent
from the shell PATH; its DST-aware local timestamp was retained.

Documentation validation: `git diff --check` passes; all 247 local links in
the six touched Markdown files resolve. Only documentation changed, so no
model/test execution was needed. Eleven primary-source URLs are cited in the
note, with measured project results kept separate from proposed experiments.

