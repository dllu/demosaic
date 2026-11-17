# Whole-scene context: primary benchmark admission

**The full427 and known/unseen camera evaluation is running on CPU.** This
report records input preservation and numerical qualification; it contains no
completed new primary score. The three2k EMA endpoints and matched V120 control
are identified in the [completed64-source study](whole-scene-context-development64.md).
GPU training continues with the [larger corpus](full-corpus-scaling.md).

[Frozen plans, executed sources, qualifications and preserved failures](results/whole-scene-context-primary-admission-v1/publication.json) ·
[Independent evidence audit](results/whole-scene-context-primary-admission-v1/independent-review.json).

## Preserve the original scored observation

The fixed panel has427 photos plus16 separate synthetic sources, seven
conditions and four CFAs:3,108 native batches/12,404 examples. Known cameras
have four scenes/eight captures/72 crops in24 batches; unseen cameras have
five scenes/ten captures/90 crops in30 batches. The historical seed, crops,
five model arguments and photographic GT are unchanged. Photo means balance
28 cases within each source; camera means balance crops within capture and
captures within scene. The real primary score measures clean CFA samples;
independently demosaiced RGB is auxiliary, not exact RGB GT.

[The exporter](../scripts/export_canonical_primary_inputs.py) executes only
the historical physical preparation on CUDA, with a2GiB allocation cap.
All3,162 batches match the old five-argument witnesses exactly, including every
photo target. It makes **zero learned forwards**, adopts30 closed preflight
batches without redrawing, and finishes in172.083 seconds with0.107GiB peak
Torch CUDA allocation. Preflight separately took12.737 seconds. Storage is
inside the project; external input caches are read-only. This short physical
export ran alongside training, without changing its PID, recipe or schedule.
Training timing was not exclusive and resulting weights are not claimed
bit-identical to an execution without concurrent activity.

All18 cached public noisy RAWs were independently decoded and all162 native
camera crop RAW/WB/matrix/CFA observations match. References never supply scene
context. The photo composer retains every old crop pixel; odd source origins
are rebased by at most one pixel in the surrounding CFA frame. Earlier inventory
finds315/427 sources have an odd crop origin on at least one axis. The surrounding
noisy field uses a separately keyed draw; original scored pixels remain exact.

## Qualify CPU execution with a matched control

Eight actual V120 CPU probes cover positive noise, ADC, shadows, highlights,
known/unseen cameras and final incomplete batches. The original CPU-versus-GPU
bound, maximum0.25/RMS0.025 DN16, **failed** on the highlight probe:
maximum0.343745/RMS0.030953 DN16, at an unclipped value approximately1.836.
Using channels-last did not fix it. The failed receipts stay failed.

Analysis of those saved predictions finds at most0.00000763 dB per-source
sRGB-PSNR deviation, but that observation does not relax the original bound.
Instead, V120 and all candidates are evaluated on the **same CPU FP32 path**.
The eight existing CPU parent outputs are reused after all eight reproduce
byte-exactly with the chosen four-thread policy. Historical GPU parent outputs
remain historical evidence rather than the new matched control.

The original color and metric bytes and source/camera aggregation formulas are
verified unchanged. CPU Gaussian SSIM encountered a reproducible oneDNN
grouped-convolution JIT `label is too far` failure. Metrics now use the reference
CPU convolution with oneDNN disabled only during metric computation; neural
model execution keeps its oneDNN policy. The original failures, an unrelated
JSON-coordinate serialization failure and corrected analysis are preserved.
Undefined metrics serialize as null.

## Shared features retain the native model computation

[The scene wrapper](../src/demosaic/scene_restoration.py) accepts one scene per
crop while retaining the original local B4 encoder/trunk call. Actual pooled
and spatial endpoints on two distinct fields produce bit-identical results
when heterogeneous B4 composition is compared with separate B2 calls.

[FrozenDinoReplay](../src/demosaic/frozen_encoder_replay.py) shares only identical
frozen CPU DINO requests across checkpoints. Class/config/state and actual input
fingerprints must match; consumers must leave features unchanged. Inference
mode is required, and forwards are restored on success or failure. Actual
four-model independent/replayed B4 outputs are byte-identical; four local
requests become one execution plus three checked replays. All learned trunks
and projections still run. Fifty scene/data/inference tests and five replay
tests pass; these numerical checks are not quality results.

Complete actual noisy scene fields and four frozen feature maps are saved
locally. Scene features are shared across pooled/spatial endpoints; original
targets never enter that encoder. The three-case learned preflight finishes in
204.773 seconds: nine new restoration forwards, three actual local DINO calls,
six checked local replays and six scene encodings; three existing CPU parent
outputs are reused. Its frozen DINO remains unchanged.

## Running collection and remaining coverage

[The collector](../scripts/collect_scene_primary.py) adopts all three preflight
cases without replay. It evaluates every fixed case, with no quality-based
stopping or checkpoint selection. CPU affinity is0/1/4/5, four threads, nice10;
there are no new CUDA model calls or optimizer updates. Admission requires
40GiB available memory, runtime floor24GiB and internal-disk floor192GiB, with
a36-hour runtime bound. Exact ownership/launch and one timestamped progress
observation are archived; the live worker can advance beyond that snapshot.

Training completion, numerical completion and actual native viewing remain
separate. Until comparable panels close, the chart/registry stays through V131;
no64-source or preflight mean is substituted. Both protected GFX families and
eight development boards are already viewed for these exact2k endpoints.
The scaling arm's first1,000 updates are a trajectory milestone, with no new
full427/camera/fence quality claim. Complete primary scores and their
source-bound history update remain pending while this collection runs.
