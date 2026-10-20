# Audit width folding against the genuine restoration trunk

The preceding goal turn was progress: the retained V43/RawNIND camera
comparisons were actually viewed beside the completed new endpoints, with
26 selected source triplets/38 unique cells published in commit ebe50a7.
The full project goal remains active and the original quality criteria stay
fixed. The new numerical model-quality results remain unread before the
remaining native review.

At05:13:42UTC the exact full427 worker703974/create1792471179.23 is live and
running, with64,867 of74,424 records. Its controller622316 remains the owner.
This is a verified wait for actual ongoing inference. Known/unseen stages are
already complete; no process was restarted. The newly edited files are not
bound inputs of the active review or either deferred CUDA probe plan.

While inference runs, I inspected the recent Pochimireddy et al. CVPR2026
mobile RAW-video paper and its publisher project page. The primary project
hosts its PDF even though the initial CVF fetch returned403. The inspected
project still marks code/data as coming soon. PDF/HTML/figure are cached under
`.cache/research/mobile-raw-CVPR2026-v1/`; no publisher model code, weights or
training data were incorporated. The width/channel restructuring motivates
an independent operator/compute check, not a reproduction of NPU results.

The new script independently derives the phase mapping for a dense3×3,
stride1/padding1 convolution after folding adjacent width pixels into channels.
Forty-eight cases use six genuine V63 EMA kernels, FP64/FP32, even/odd widths
and contiguous/channels-last input and weight layouts. FP64 maximum difference
is4.44e−15 and FP32 reaches5.96e−6 feature units. A nonzero-bias control checks
all padded boundaries against NumPy. Independent scalar accumulation reproduces
that control within5.00e−16.

My first whole-trunk FP64 fixture was invalid: the actual trunk deliberately
casts its head input to FP32, so converting its weights to double failed.
That source/failed attempt is retained in CPU-v1. The corrected CPU-v2 limits
whole-trunk execution to supported FP32; final CPU-v3 also covers actual
channels-last weight layouts and saves the independent-control arrays. No
production source changed to accommodate the diagnostic.

All64 genuine EMA trunk tensors load strictly. The actual FP32 whole trunk on
generated native32/B1 inputs differs by3.28e−7/4.17e−7 normalized output units
in contiguous/channels-last formats. It excludes DINO/measurement offsets,
physical inversion and photographs; this is not full-model or RGB16 parity.
Both trunk-class ASTs match the frozen source used by the live comparison.
CPU RNG is unchanged and CUDA remains hidden.

The64-layer executed census matches independent topology arithmetic:
2,117,568 dense MACs per native pixel. At B4/native512 the original trunk
uses2.22043T MACs; the dense local fold uses4.38932T, an increase of97.68%.
The58 affected kernels require4× dense storage and retain the same even-width
activation element count, before extra packing/unpacking allocations. This
does not measure actual peak memory or CUDA time. A target-hardware benefit
remains possible but unestablished; no new GPU job or serving rewrite follows.

Final artifacts are in
`/mnt/external/demosaic/experiments/width-fold-convolution-CPU-v3/`:
probe SHA256`e69c0d98b46eb0f4225622fd10c7e58c990f72aae5d7bf85a59f0b9cdd9fe548`,
independent audit`025a65c1f83b9a2c473ab02e758c49332cdce980d14cc01e0e362b8e37cdc3a7`.
The complete receipts are published with `docs/width-fold-convolution.md`.
Ruff lint/format and diff checks pass. SOTA, decisive real-photo superiority
and100MP/10s remain unmet/unproven. Complete the live quality/native review
before selecting another training experiment.
