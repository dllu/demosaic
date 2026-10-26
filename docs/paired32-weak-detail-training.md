# V120/V121: paired-data control and weak photographic targets

**V120 is training from V115 Small; V121 is queued after it.** Both passed
discarded16-update CPU and CUDA checks. This follows V119's photographic gain,
known-camera regression and large ADC color tail. The paired-set control tests
whether restoring the corrected32-ID set helps the overall balance. The second
arm tests the prepared cleaner corpus and expanded weak-detail material bank.
There is no new endpoint quality result yet.

[Started-run evidence and exact owners](results/v120-v121-training-start-v1.json) ·
[Launch verification](results/v120-v121-training-start-verification-v1.json) ·
[V120 recipe](../configs/quality-v115-paired32-control-v120.yaml) ·
[V121 recipe](../configs/quality-v115-reviewed-weak-detail-v121.yaml) ·
[Completed V119 comparison](v119-quality.md).

## Controlled differences

| Setting | V119, completed | V120, running | V121, queued |
| --- | --- | --- | --- |
| Initializer | Final V115 Small EMA | Same weights, immutable copy | Same weights, immutable copy |
| Commons sources |90,791 |90,791 |90,787 |
| Reviewed photographic regions |6 |6 |14 |
| Paired set |83 publisher IDs /71 groups |Corrected original32 groups |Same corrected32 |
| Native camera targets |128 source IDs |Unchanged |Unchanged |
| Source-loss diagnostics |Off |Every100 updates, Commons only |Same |
| Seed / full budget |65 /20,000 |65 /20,000 |65 /20,000 |

V120 retains V119's Commons source reader, six regions, camera probabilities,
architecture, noise generation and training budget. It replaces the expanded
paired set with the original32-ID set, retaining all four reviewed reference
mask corrections. Per-camera probabilities remain Sony75%, Canon6D12.5%,
NikonZ6 9.375%, NikonD40 3.125%; this does not restore the old uniform sampler's
exact random sequence. Source tracing adds metadata and detached diagnostics;
tests and actual checks cover its lack of neural/RNG side effects.

V121 differs from V120 only in Commons membership and its bound ROI catalogue,
plus output paths/descriptive notes. Four further visually unsuitable sources
are withheld. The fourteen-region bank retains the original six and adds eight
inspected contexts with weak plaster cracks, brick joints, wavelets, sand
ripples and other material detail. The5% conditional-photo ROI quota is fixed.
This tests the combined cleanup/material-bank intervention, not the separate
effect of source count or individual regions.
[Source decisions](next-source-tail-review.md) ·
[Weak photographic targets](weak-photographic-targets.md).

Both use fresh AdamW/EMA from V115, B16/native256/BF16, LR1e−5,200 warmup steps,
50% Commons/procedural,25% paired and25% native. The declared sequence has
10,013/5,021/4,966 batches per arm. Only the selected domain is loaded.
Targets retain4× binning→geometry→area2, zero optical PSFs, legacy weak textures
.15, photographic contrast attenuation.25, reconstruction epsilon.0003,
paired epsilon.0001 and band loss off. This keeps quality work separate from
another batch/speed sweep.

The initializer is the immutable checkpoint with SHA256
`fee5d05c599cb32f5a1e587c31979f040a06152c8e14676481eee83a4ce04d84`.
Official DINOv3 ConvNeXt-Small revision
`421020015aa4266363db803b6049a529999afb1e` stays frozen, hash
`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.
No feature fit is repeated. The main3879/3880 scene, additional3842/3835 mesh,
their siblings and all protected evaluation sources remain outside training.

## Actual implementation checks

Each arm completes16 CPU64/B1/FP32 updates and16 CUDA256/B16/BF16 updates,
covering11 Commons,four paired and one native batch. Each verifies all91 initial
EMA tensors, the official frozen encoder,89 fresh AdamW states and correct
step counts, finite model/EMA/optimizer values, exact manifests and actual source
archive. Smokes are discarded; production starts afresh from the same parent.

V120's twelve shared Commons/native input batches in each check exactly match
retained V119 checks. V121's five paired/native batches exactly match V120 in
each check. Production's first V120 loss equals its CUDA check's first loss.
These establish implementation and shared-input behavior, not endpoint quality.

Each actual source diagnostic temporarily forbids neural Module calls and
checks unchanged Python, NumPy, Torch CPU/CUDA random states. It scores existing
predictions with detached FP32 singleton losses. At the published launch receipt,
V120 has reached logged step175 and32 diagnostic examples; those are procedural
and photographic draws, not32 independent photographs or additive training-loss
contributions. High loss nominates visual inspection rather than automatic
source removal. [Trace definitions and limitations](source-loss-diagnostics.md).

The [bounded source reviews](current-source-loss-review.md) inspect28 photographs
from the first800 updates and28 further sources nominated through5000, with
larger native views where needed. Fifty-five are retained; one roofing
advertisement is withheld from the prepared future90786-source snapshot.
The original V120/V121 cohorts remain unchanged. The newer
[V122/V123 architectural trials](learned-raw-frequency-training.md) use that
future snapshot; this inspection is not an endpoint-performance result.

Preparation verifies the actual clean/paired/native cached readers without
RAW decoding or neural calls. A first preflight used the wrong native-field
name; the corrected version uses `camera_rgb`, the actual clean-reader rows and
native256 output shape. An initial launcher import failed before any worker
because its path was relative to the wrong directory. Both failures remain
preserved; the corrected launcher uses absolute frozen import paths. Neither
failure consumed model forwards or optimizer updates.

## Endpoint review

The exact training controller owns both sequential full runs. Eight queued
single-view FP32 stages evaluate only the new endpoints: photo, known/unseen
measured cameras, weak carriers, color, standing GFX, highlights and the complete
101.996MP frame. Together they declare9,172 root/encoder calls and28,380 primary/
analytic observations. Inputs must match the original completed witnesses.
Existing V115/V117/V119 controls are reused from saved arrays.

The queued independent CPU audit rebuilds all28,380 observations without new
inference/noise/RAW work. Four full saved-output contrasts are V119→V120,
V115→V120,V120→V121 and V117→V121. Each includes matched primary/analytic rows,
native material/all six GFX regions and427-photo local detail over5,124 cases
and96,075 reused GT blocks. Both linear/sRGB RGB16 exports per endpoint receive
native quantization checks at921,600 channel values altogether.

Before recommending either endpoint, inspect at least two native noisy/restored/
exact-synthetic-GT triplets, the six main GFX regions, adverse camera/color cases
and the fine green mesh under the two existing fixed profiles. Main3879/3880
and mesh3842/3835 references remain independently captured and **not exact GT**.
Reports record source/ROI/checkpoint/conditioning/display, with no resized crop
pixels. Completed useful gains and weaknesses update the current guides directly.

Workers retain48/24GiB start/runtime available-RAM floors,24GiB CUDA quota,
128/96GiB internal disk floors and208GiB external reserve. Failures preserve
actual work without automatic retry or budget extension. V114 general,
V115 known-camera and V117 photo choices remain available while these trials
train; no result is inferred from a successful launch.
