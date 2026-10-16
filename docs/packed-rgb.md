# Packed-resolution RGB restoration experiment

`model.rgb_processing_scale: 2` runs the existing pretrained restoration CNN
on half the sensor height/width. The full-resolution path remains the default
(`1`). This is an experimental architecture; its six-step engineering smoke
does not establish a quality or speed improvement.

The packed path retains all four Bayer measurements, their individual color
labels, the existing camera/noise/black/white features and genuine frozen DINOv3
ViT-S/16 context. DINO sees the original camera rendering; its native token grid
matches the packed CNN's middle resolution. No additional foundation weights
or image data are introduced.

An area-2 mean of normalized variance-stabilized Malvar RGB feeds the pretrained
RGB trunk. Its noise proxy uses the actual MHC-plus-area kernel energy: the
unit-WB interior RMS gain is **.6564979553**, not .5. Small deterministic basis
impulses derive those kernels for all four Bayer layouts, with input/output
white-balance ratios for Gaussian profiles. This corrects marginal variance;
it does not whiten correlated RGB noise, and GAT unit variance remains an
approximation at low counts.

The CNN predicts a coarse RGB correction. A new zero-initialized projection
exposes the separate sensor measurements to its first layer; a second zero
head uses its 64 output features and those 16 measurement/identity features
to predict 12 individual output values per packed cell, then pixel-shuffles
them to native RGB. Original full-resolution MHC detail bypasses the coarse
correction. Thus the input is not restricted to three averaged RGB values,
and the output is not restricted to an interpolated low-resolution image.
The bypass initially retains fine noise as well as detail; training must learn
to remove it. The changed spatial/noise statistics also make warm-start quality
uncertain despite reusing every original CNN weight.

Normalization, physical feature construction, projection heads, native skip,
expectation inverse and final output keep IEEE FP32 math; deep CNN/DINO use the
existing BF16 training / FP16 inference policy. Arbitrary even sensor dimensions
are padded on the packed grid and cropped back without resizing output pixels.
Physical kernels are stored as a three-dimensional nonpersistent buffer so
the production channels-last transfer works. Checkpoint configuration records
the scale; warm initialization allows exactly the new phase-module prefixes.
Resume still requires the same parameter set.

[Engineering receipt](results/packed-rgb-smoke.json): six real CUDA updates,
batch two, pinned DINO revision `114c1379950215c8b35dfcd4e90a5c251dde0d32`,
the same V32-step2000 EMA parent as recorded, all three selected domains,
finite losses/gradient norms and nonzero updates in both new phase modules.
It ran alongside an existing evaluation; its timings are not a benchmark.
The first attempt stopped before training because of a buffer memory-format
error; the receipt retains that failed run separately.

Tests compare the default branch bit-for-bit against a SHA-pinned pre-change
source fixture (linear RGB, stabilized and physically anchored modes), preserve
native 16-bit ramps under BF16 for every CFA and odd packed dimensions, route
an individual raw phase to an individual RGB phase, check Gaussian noise gain
by Monte Carlo for every CFA, backpropagate through both new modules and load
a channels-last checkpoint with identical output. Existing pipeline/resume
tests remain part of the complete suite.

Quality selection requires a matched full-resolution control, shared parent,
data/mix/seed/schedule and batch size, checked observation hashes, real
development panels, the full 427-photo synthetic suite and native GFX foliage/
fence crops. Do not promote this variant from the smoke or a throughput result.

The queued experiment uses [V37](../configs/dino-anchored-packed-control-b16-v37.yaml)
and [V38](../configs/dino-anchored-packed-rgb-b16-v38.yaml): V34 step1000 EMA
parent `4da823a0bcff4d02335ba2a9eb04ef7c54d8e2ff7d5d96c1116e9f1ce72899b7`,
fresh AdamW/EMA, seed47, batch16, LR3e-5 with the original planned3000 schedule,
and a1000-update review. Only processing scale differs. Both use the same
complete40170-train Commons4 corpus and53 native4 captures, final area2 after
geometry, original8x validation, and25% paired /25% native /50% Commons.
No public RAW quarantine is admitted. Every logged observation must match.

Before training, the workflow waits for the full geometry review and requires
V34 to improve on V32 at the matched first1000 full-photo checkpoint. It measures
batch16 in scale1/scale2/scale2/scale1 order, then packed batches8/32/64 in both
orders. Each case starts from the same parent, excludes8 warmup updates and
times30 updates including selected-domain loading/degradation, DINO,
forward/backward, AdamW and EMA. Startup/validation/serialization are excluded.
These are shared-machine measurements. The quality trial keeps batch16 even
if another batch is faster. The workflow stops after first1000, evaluates real
development, all427 photos plus16 procedural sources and full GFX, and writes
native triplets through the standard evaluators.

Live state: `/mnt/external/demosaic/runs/packed-rgb-v37-v38-workflow.json`.
Throughput results and archived workflow:
`/mnt/external/demosaic/benchmarks/packed-rgb-v1/`.
The isolated worktree retains the experiment's source; later main-branch changes
cannot alter these queued imports. All results remain pending at setup time.
