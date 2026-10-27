# Deterministic photographic epochs for full corpus coverage

Recorded: 2026-10-27T11:13:43-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress in8b1dea4: forty additional source
inspections and prepared90778/33 data. This turn verifies the active V124 worker
and original mean-loss/spatial/quota review owners, then addresses source
omissions within the same quality-training budget. The PROMPT quality, broad
RawNIND superiority and100MP/10s goals remain unproven; no completion claim.

Implemented optional ordinary-photograph epoch order in
`src/demosaic/photo_epoch_order.py`, with metadata preparation in
`scripts/prepare_photo_epoch_order.py` and reader/training integration. A frozen
int32 global-index array binds exact manifest/ordered IDs, family/ROI selection,
seed, batch/domain layout and horizon. Each complete ordinary epoch shuffles all
active sources once. Reviewed and procedural slots do not advance it. Default
replacement sampling remains unchanged. Resume rejects changed header identity
before constructing a model; checkpoints preserve header and payload bytes.
Different CPU/CUDA check layouts need separately generated matching orders.
No production trial is launched with this option and no new model version is
assigned before its controlled quality comparison.

Prospective90778/33,seed70,20k,B16,.25/.25 paired/native,.05 reviewed quota:
10046Commons/4965native/4989paired steps,106823ordinary/5601reviewed/48312procedural
Commons draws. Replacement visits62873IDs (69.26%); epochs visit90778 (100%),
first completing atstep17039. The partial second epoch has16045distinct IDs;
74733sources haveone ordinary visit and16045havetwo. Coverage alone is not
restoration/detail/PSNR evidence. No future policy replaces an active/queued
source set, schedule, budget, architecture or retained control.

Private root:`.cache/current-quality-20261023-v1/photo-epoch-order-90778-v1/`.
Prepared header SHA256:
`d7ab526c18ca9724c8a580e3baff7cb4beac3e238749d173992d332bdfe05633`.
The preview recipe inconfigs exactly matches the audited selection/layout keys.
Full audit follows321472 actual current/frozen-reader metadata paths, stopping
before pixels/generation, and checks all20k domain choices. All ordinary IDs
match the array; complete epochs include every active source exactly once and
partial epochs have no repeats. All procedural/reviewed source choices and
local RNG states remain exact. Eighty-eight additional real clean reads compare
new-default pixels with the original frozen V131 reader, exercise the ordered
procedural/reviewed paths and four newly ordered sources.10223616common FP32
values match. Global Python/NumPy/Torch RNG states unchanged; CUDA uninitialized.
No source-order analysis neural/noise/RAW/optimizer work. The toy unit tests
are separate;83tests passed23.99s, including actual resumed-weight equality,
source-snapshot equality and early changed-order rejection. Ruff passes.

[Current documentation and limits](../docs/photographic-epoch-order.md) ·
[Public audit/source/test receipt](../docs/results/photo-epoch-order-v1.json).
README/current model/source guide/pipeline/research now document the optional
implementation without treating source coverage as a trained gain. Requirements
also refresh the newest prepared snapshot to90778/33. The existing best V120
selector, performance-history points, current GFX comparisons and original
machine receipts stay intact.

Publication verification passes1770 content bindings,20 frozen plans and174local
links. All17 checked training/review controllers and V124's exact worker remain
live;61other core modules match the original frozen V131 bytes. Audited reader,
training integration, new order class and preparer match their frozen executed
source bytes. V124's latest logged step at final check is12650. Existing current
selector SHA remains exact. `docs/results/photo-epoch-order-publication-v1.json`
records these checks. No existing receipt was rewritten.
