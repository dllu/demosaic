# Profile the current packed models after quality evaluation

Two bounded GPU profiles are queued after the exact mixed16 quarter-review
owner. The profiler currently waits without children. No GPU profile or new
speed result is available yet. Training and quality evaluation retain priority.

[Frozen plan, actual owners, executed sources and CPU audits](results/mixed16-packed-inference-profile-queue-v1.json).
Live status:
`/mnt/external/demosaic/runs/mixed16-packed-profile-after-quarter-v1.json`.

The completed first32k review observes151.54/169.39s full GFX FP32 restoration,
well above10s. The [operator census](packed-isotropic-operator-counts.md)
counts arithmetic but cannot identify the GPU bottleneck. This profiler will
measure the actual10k/160k-example V72/V73 endpoints after all numerical quality
panels and their owners finish. It reruns the frozen completed-training-boundary
validator on CPU before allowing either GPU child.

The fixed GPU input is the existing four native512 GFX contexts, batch4,
channels-last. IEEE FP32 disables AMP and TF32, matching the full quality review.
Three warmups precede five synchronized unhooked forwards, five forwards with
branch hooks and one operator trace. Each model runs in its own process, with
32GiB minimum available RAM,500GiB disk headroom and a300-second child timeout.
Failure stops the queue without an automatic restart or adoption.

Thirteen ranges cover the RAW core, two stems, local blocks, six groups,
upsampling, decoder and head. DINO adds its context and backbone ranges.
These intervals overlap: the RAW core includes DINO and the context includes
its backbone. They must not be summed. The trace records actual operators,
device activities and allocations separately from unhooked samples. Resident
forward samples exclude transfers, tiling/blending, decoding and encoding;
they cannot establish a100MP speed or a hardware optimum on a shared machine.

Both preserved2k checkpoints pass actual CPU instrumentation preflights on the
top-left native256 part of the first context. All unhooked, hooked and traced
RGB values match bit for bit, with model/full DINO state and RNG unchanged.
All13/15 ranges execute twice during sampling and once in each trace. CUDA
remains uninitialized, with zero device events.

An independent input replay verifies393,216 float32 output values exactly,
all28 named trace ranges, the variance/shot/read conditioning, executed-source
archives and identical model source in the frozen future GPU job. It uses the
same model implementation and supplies input/instrumentation consistency
evidence. Twenty focused hook, cleanup, tensor-hash and owner-gate tests pass;
Ruff passes. A terminal status with a still-live owner is rejected.

The future GPU runs must retain exact repeated/hooked/traced outputs and model
and CPU/CUDA RNG state, and contain genuine positive-duration CUDA events.
No weights, precision, algorithm, training source or production default changes.
Read the actual trace before choosing a speed change. Any later optimization
still needs its own numerical, native visual and full-frame validation. The
[separate FP16 compilation rejection](packed-isotropic-compilation.md) remains
unchanged. Manual quality review and model promotion remain pending.
