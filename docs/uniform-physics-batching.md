# Batch physical operations for a shared inference noise prior

An isolated CPU prototype produces identical physical fields and genuine V63
predictions while reducing repeated Python calls for a scalar shot/read prior.
The [completed CUDA/native review](uniform-physics-CUDA-review.md) now checks
all eight full outputs exactly across13.37million RGB values. Resident timing
is mixed: V43 is.87% slower and V63 is1.59% faster. No production integration
or new full-frame speed result follows. The CPU preparation record below is
retained; V90/V91's separate [quality review](late-rgb-original4k-review.md)
is also complete without promotion.

[Executed sources, inputs, checkpoint, arrays and comparison receipt](results/uniform-physics-CPU-v1.json).

The current stabilized forward loops over images for the GAT, initial MHC
demosaicing and expectation inverse, even when `set_noise` receives one scalar
profile for the whole tile batch. The prototype applies each operation to that
batch directly. Per-image normalization, physical anchors, frozen DINO, neural
precision, prediction and inverse expressions remain intact. The original
multi-profile branches remain verbatim in the generated AST, including a vector
containing equal profiles. This is an inference engineering experiment without
an optimizer, new weights or a quality claim.

## Executed CPU checks

The probe generates its candidate forward in memory from the hash-guarded
current method. Replacing its two changed subtrees with their originals must
reproduce the complete original AST exactly. Both method sources, all47 model
modules and the executed driver are preserved under
`/mnt/external/demosaic/experiments/uniform-physics-CPU-v1/`.

All48 component cases pass exact byte and stride comparisons for four returned
fields: transformed measurements, noise proxy, initial RGB and inverse RGB.
That covers192 fields/378,048 values. Cases include pure Poisson, shot/read,
read-dominated, Gaussian and ADC-only priors; scalar B1/B4; both memory layouts;
even/odd packed extents; negative measurements; all four Bayer patterns in B4;
per-image WB; and mixed/equal-vector fallback profiles. Component inputs are
deterministic nonphotographic fields.

The genuine V63 original20k EMA then runs on the same four cached GFX subcontexts
used by the earlier physics cleanups: native80×64 at relative
`[216,224,80,64]` inside the saved512px contexts. All184,320 complete RGB values
are byte-identical across scalar GFX noise, equal-vector fallback and scalar
ADC-only conditioning. All model/DINO state, parameter identities and RNG remain
unchanged; CUDA stays hidden and uninitialized.

Checkpoint SHA256:
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
GFX shot/read variance:
`.0014635775921166604 / .0000010715704128646712`.
No reference image, GT score, training objective or source-drive access occurs.
This does not establish equivalence at the full512px serving context size.

Measured Python calls for the four-context genuine forward:

| Conditioning | Operation | Original | Prototype |
| --- | --- | ---: | ---: |
| Scalar GFX | MHC |5|2|
| Scalar GFX | GAT forward |8|5|
| Scalar GFX | GAT inverse |4|1|
| Equal-vector fallback | MHC / forward / inverse |5 /8 /4|5 /8 /4|
| Scalar ADC-only | MHC |5|2|

The ordinary camera preview still needs one MHC call. Four scalar GAT white-anchor
calls also remain. These are Python call counts, not device kernel counts or
latency measurements. Batched MHC can use different CUDA convolution algorithms
and larger intermediate allocations; CPU agreement does not settle GPU
numerics or peak memory.

An independent NumPy read verifies every saved full-model array's dtype, shape,
finiteness, hash and byte equality. All66 receipt references verify. The scalar
GFX baseline also matches the earlier inverse/physical cleanup's saved output
exactly, file SHA256
`425cc15ec6282b5caed94f64387efaf3e43d4608710094a122495ef8dc17dcad`.
Ruff passes. No additional project tests or GPU jobs were started.

## Reproduction and remaining measurement

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONPATH=.:src:scripts \
  uv run --no-sync python scripts/probe_uniform_physics_cpu.py \
  /mnt/external/demosaic/experiments/CHOOSE-NEW-CPU-OUTPUT
```

The existing output is immutable; a new execution needs a new directory. The
probe checks memory/disk headroom before loading the model. Future CUDA work
must wait for the exact training and complete quality-review owners to exit,
then compare unchanged-weight predictions at actual serving dimensions and
measure both policies with the same precision and inputs. The existing
1DN16 maximum/.25DN16 RMS full-output gate should remain unchanged. No production
integration follows from this CPU result alone.

## Deferred GPU validation

The actual frozen worker now passes its
[CPU switching preflight](results/uniform-physics-worker-CPU-v1.json): eight
unchanged V43/V63 comparisons,307,200 RGB values, repeated candidate predictions
and restored-original predictions all match bytes. These are native80×64
subcontexts in channels-last format, including both saved photos and the GFX/
all-CFA analytic inputs. Model/DINO state, parameter identities and RNG remain
unchanged. This extends the earlier contiguous V63 full-model check; it does
not substitute for actual CUDA or native512 validation.

The [queued GPU plan and verified waiting-owner receipt](results/uniform-physics-CUDA-queue-v1.json)
bind67 source/checkpoint/input files, including all47 model modules. The actual
CUDA entry point was called while all six predecessor owners were verified
live; it rejected before CUDA initialization or output creation. Fourteen
focused tests pass for the original numerical limits, unclipped comparisons,
owner/plan identities, failed and incomplete dependencies, lingering children
and separate system/external disk floors. No production source changed.

The controller is queued under
`/mnt/external/demosaic/experiments/uniform-physics-CUDA-v1/`. At the recorded
verification it was live, child-free,18.1MiB RSS, without Torch/CUDA libraries
mapped, and no GPU output/log existed. This is a historical liveness snapshot;
read the actual `status.json` and verify PID/creation time before acting.

It waits for successful exact exits of the original4000 training, all ten
quality stages, CPU closure, retained references and native report packaging.
The fixed review may still require actual human/agent viewing at that point.
After48GiB available RAM remains stable for60 seconds, the probe can launch
once with a16GiB CUDA allocator cap,24GiB runtime RAM floor,64GiB system disk
reserve and500GiB external reserve. Dependency/resource/worker bounds are
24hours/1hour/20minutes; failure does not trigger a retry or model change.

The future GPU checks cover both mature checkpoints, both full native256 photo
inputs, all four unchanged native512 GFX regions and the low/high-signal
native512 all-CFA input: eight complete output pairs. The existing1 maximum/
.25 RMS DN16 limits apply before clipping, rendering or quantization. All
eight must pass before three warmups and four resident timings per policy,
in ABBA/BAAB order, for each model. IEEE FP32, cuDNN autotuning, channels-last
and the exact input noise conditioning stay fixed. Timings exclude search,
loading, transfers, tiling, blending, decoding and export. Independent saved-array
and native-crop review remain pending; no GPU speed or integration result is
claimed by this queue.

## Saved-array and native review preparation

The deferred GPU result now has a tested CPU review path. The
[historical integration receipt](results/uniform-physics-review-preflight-v2.json)
replays the six existing TF32x3 GPU array pairs, independently reducing all
7,077,888 unquantized RGB values with NumPy FP64 and scalar `math.fsum`.
It reproduces the previous numerical and timing arithmetic. These are historical
TF32x3 outputs, explicitly labelled as such, with no new batching inference,
timing or quality result.

The same integration re-renders24 native160px triplets and checks all72 panel
pixel arrays against the earlier report. Four new comparison boards contain48
native cells: two exact-GT photos per mature model and the four standing GFX
regions. Photo targets replay from their original8×-binned source-cache ROIs;
noisy/reference pixels remain equal across methods. The ISO100 GFX panels stay
labelled as qualitative references. No crop pixels are resized. The new boards
deduplicate the photo noisy/reference rows; their actual crop pixels match the
old layout exactly. Actual viewing of these newly built boards is not claimed.

The first integration attempt preserved its source/logs and partial outputs
under `uniform-physics-review-preflight-v1/`: the final panel comparison used
`original` to look up the historical `IEEE` policy. Only that historical lookup
was corrected. The separate v2 execution passes; no model or GPU run failed.
Twenty-six focused tests also pass, including unclipped negative values,
changed metrics, duplicate cases, small CPU/nonfinite arrays, timing order,
exact owner/plan checks and completed/rejected versus incomplete dependencies.

[Verified CPU-review queue](results/uniform-physics-review-queue-v1.json).
Its source-frozen owner waits behind the exact GPU controller and worker,
without importing Torch/CUDA while waiting. All60 review bindings are fixed.
After a complete GPU result it independently verifies all eight full output
pairs, then prepares the24 triplets/four boards. On numerical rejection it
audits the available failed prefix and produces no speed or full-native-package
claim. It does not retry a failed GPU run.

The review uses32GiB available RAM to start,24GiB while active,64GiB system and
500GiB external disk reserves. Dependency/resource/individual CPU-stage bounds
are30hours/1hour/3minutes. Only its exact owned child can be stopped on a bound.
The final package remains explicitly awaiting actual inspection, with no
promotion, default change, full-frame measurement or quality conclusion.

Scripts: `audit_uniform_physics_arrays.py`, `render_uniform_physics_native.py`,
`preflight_uniform_physics_review.py` and `watch_uniform_physics_review.py`.
The queued plan/status and future outputs reside under
`/mnt/external/demosaic/experiments/uniform-physics-CUDA-review-v1/`.
