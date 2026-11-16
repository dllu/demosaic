# Matched endpoint detail review is queued

The [full-model RAW-attention comparison](raw-spatial-continuation.md) now has a
source-frozen review queue. It waits for the exact training controller to finish
both 20k endpoints, then collects **102 saved inputs per model** and independently
audits their numerical metrics and native pixels. No completed-model quality
result is available yet. V120 remains the recommendation.

## The same weak-detail and photographic evidence

The queue reuses the original retained-input panel and all saved V120 predictions:

| Inputs per model | Coverage |
| --- | --- |
| 64 | Four material sources under four shadow/noise conditions and four CFAs |
| 16 | Ordinary bark, fur, fine wood and field references under four CFAs |
| 16 | The same four materials at 2.5% contrast with ADC-only noise, four CFAs |
| 4 | DSCF3879/3880 sky, building, foliage and chain-link fence |
| 2 | DSCF3842/3835 native 768 context at nominal and nearby-capture profiles; both left/right cab ROIs |

These are repeated conditions from four material sources, not 102 independent
photographs. Constructed bark/fur targets retain their exact-target labels;
independently binned photo references and real ISO100/AHD captures remain
accurately labeled approximate/qualitative references. Real captures are not
pixelwise scoring targets. All protected captures/JPEGs/siblings remain excluded
from training. Only retained arrays are opened; original RAW media are untouched.

V132 also receives the newly saved V131 endpoint predictions as controls, without
another V131 forward. Every comparison uses identical source/ROI, RAW noise
conditioning, display exposure, WB/matrix and native crop pixels. The report
prepares noisy/restored/reference triplets, including exact constructed-GT
triplets, and ordinary multi-method comparisons.

Both original-pixel camera JPEGs now appear explicitly in each cab comparison,
at both ROIs/profiles. They retain their camera-rendered sRGB pixels, with no
additional RAW display transform or resizing. They are separate qualitative
comparators, not exact GT. All four cached native 160 JPEG arrays are bound and
checked. The independent auditor verifies their actual displayed pixels.

## Endpoint identity before model construction

The exact controller owner and immutable training plan must agree throughout the
wait. A timeout, missing handle or failed controller never triggers a training
restart. Once the controller finishes, both result/checkpoint bindings and dead
training owners are checked. Every step/domain/clean/noisy fingerprint across
all 20,000 training observations must match between arms.

The collector then checks the saved model/EMA/Adam state, source hash, V120
lineage, seed 70, architecture and complete 20k horizon before model construction.
V131 must have 91 restoration tensors / 89 Adam states; V132 must have 114 / 112,
including 23 spatial-branch tensors. Every Adam clock must equal 20,000, all
weights/state must be finite, and counts must include 640 validation forwards,
20,640 encoder calls and 320,000 target contexts.

Each actual inference uses the exact retained input fingerprints and IEEE FP32,
with autocast/TF32 disabled. Full model/backbone hashes and Python/NumPy/Torch/
CUDA RNG must remain unchanged. The total budget is 204 root/DINO calls, with
zero new source/noise construction, RAW decodes or optimizer updates.

CPU analysis computes photo/detail metrics and native boards. A separate process
that does not import Torch independently recomputes mirrored-FFT DCT16 metrics,
channelwise display transforms and every published PNG cell. Actual native
viewing remains a required next step. The broader 427-photo/camera/flat/full-frame
review is separate; this targeted panel does not establish broad model quality.

## Executed preparation and coverage correction

An actual retained 15,000-step checkpoint is rejected as an incomplete endpoint
with zero neural constructions/forwards and no CUDA initialization. Its source
stamp matches the expected original training package. **86 focused tests pass**,
including incomplete clocks/sources/lineage, changed controller identities,
training hashes, native-display bindings, actual child-process success/failure,
relaunch refusal, and real CPU rendering/independent auditing of both legacy
and extended JPEG boards. Ruff passes.

The first waiting queue retained JPEG metadata but used an older reporter that
omitted JPEG pixel columns. It was superseded before any collection, with its
source/plan/status/log and zero-forward handoff preserved. Training was not
signalled. The corrected queue adopts the identical collector's real checkpoint
admission proof and adds the explicit JPEG cells/audit; it repeats no neural
work. Historical report defaults and existing receipts remain intact.

The queue uses 52 GiB RAM admission, 12 GiB CUDA allocation cap and 32 GiB runtime
floor; internal free-space admission/reserve is 128/96 GiB and external read-only
admission/reserve 96/64 GiB. Per-collector and CPU-analysis limits are 1h/30min;
training's original horizons and worker limits are unchanged. There is no
automatic retry or promotion.

[Queue](../scripts/queue_raw_spatial_endpoints.py) ·
[Collector](../scripts/collect_retained_checkpoint_pilot.py) ·
[Focused tests](../tests/test_raw_spatial_endpoints.py) ·
[Exact source, launch, admission and handoff evidence](results/raw-spatial-endpoint-review-v1/publication.json).
