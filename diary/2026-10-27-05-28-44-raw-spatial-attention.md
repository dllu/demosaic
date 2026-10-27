# Prototype phase-preserving spatial attention for fine RAW detail

Recorded: 2026-10-27T05:28:44-07:00 (America/Los_Angeles).

The preceding goal turn made concrete progress by closing/publishing the full
V122/V123 frequency review, native comparisons and56-endpoint PSNR plot. V124's
original two-noise-view control remains live; no current production cohort,
parent, loss or deadline changed during this work.

Reviewed the existing weak-detail/gradient/input-phase diagnostics before
choosing a different operator. The full frequency trial has little natural
weak-detail recovery. The current pretrained DRUNet path is convolutional;
the recent structural-guidance JDD paper uses a native-resolution window-attention
restoration stream with frozen DINOv3 context. This motivates testing local
spatial mixing here, without a paper reproduction, new pretrained weights or
transferred benchmark claim. Primary reference:
https://arxiv.org/abs/2608.09995 (retrieved2026-10-27). Its Gaussian/sRGB evaluation
is not our physical RAW protocol. The linked GitHub repository returned404 at
this observation; no third-party code was incorporated.

Implemented optional `model.raw_spatial_features`, default false. The independent
22,664-parameter/23-tensor branch takes signed horizontal/vertical differences
of all four packed phases in restoration units, plus CFA placement and variance
conditions. Two32-wide/four-head blocks use8x8 packed windows at offsets0/4.
Padding changes the partition origin without periodic wrapping; invalid keys
are masked. Unnormalized values preserve content amplitude; residual MLPs keep
the local scale. Learned pixel shuffle and a zero projection supply64 native
stem offsets. Existing physical RGB/DINOv3 paths remain intact.

Bias-free content paths keep every per-phase spatial constant exactly zero even
after nonzero adaptation, with spatially varying variance and all four CFAs.
This does not prevent color drift in a separately trained common trunk. Initial
zero projection preserves the parent function. Constructor allocations are CPU
explicit, with a local generator preserving ambient CPU/CUDA RNG. Portable
state includes the learned tensors; missing projection state rejects.

Added conditional16-native/32-with-DINO tile alignment, including padded last
tiles and odd source borders. Original models retain their prior grid. This
preserves lattice coordinates, not equality with a full-frame forward or a
visual seam qualification. The CPU loader predates only this new-flag tiler
addition; its portable loader and direct-model/training mathematics are
unchanged. The CUDA check executes current model-source bytes.

Actual genuine-V120 discarded checks, separate frozen source/plan roots:

| Device | Geometry/precision | Updates | Root/encoder calls | Peak |
| --- | --- | ---: | ---: | ---: |
| CPU |128/B1/IEEE FP32 |16+2 |20/20 |3,242,172,416 bytes RSS |
| CUDA |256/B16/BF16 trunk, FP32 feature path |16+2 |20/20 |9,069,177,344 bytes CUDA allocation |

Each starts freshly from V120's20k EMA on90781 sources/29 reviewed regions,
seed71, the actual ordinary reconstruction loss and optimizer, with1000-step
LR horizon but only18 discarded updates. The phase schedule is nine Commons,
five paired and four native batches per check. All91 common tensors exactly
match V120 initially; the preserved16-step114-tensor model resumes exactly.
Changing the model flag rejects before any forward. All114 model/EMA tensors
and112 Adam states are finite at18, with finite nonzero gradients in every
new tensor. No old training prefix or quality observation was replayed.

The new first-batch disabled witnesses match65,536 CPU and4,194,304 CUDA
RGB/auxiliary output values exactly at zero initialization. Learned portable
EMA loading matches all114 tensors and executes one CPU forward per check.
CUDA construction is observed three times with initialized CUDA; every branch
constructor preserves CPU and CUDA RNG. Total genuine checks:36 optimizer
updates,40 root/encoder calls and306 target contexts. CUDA accounts for19 calls
in its worker plus one B1 CPU portable call. The frozen encoder remains exact.
These discarded checkpoints are not quality results or recommendations.

The first CUDA launch omitted `CUBLAS_WORKSPACE_CONFIG=:4096:8` and stopped in
execution-policy validation before any model construction/forward or prepared
batch. Its claim, source, launch, empty counters/input list and failure remain
at `raw-spatial-CUDA-implementation-v1`. Explicit recovery validates the dead
owner, zero work, absence of checkpoints/arrays and byte-identical neural source,
sets the required environment before process startup and adds an early guard.
It retains the original launch+1800s absolute deadline; the corrected check
finishes within it. There is no automatic retry or budget reset.

CPU source/receipts: `.cache/current-quality-20261023-v1/raw-spatial-implementation-v1/`.
Completed CUDA recovery: `.cache/current-quality-20261023-v1/raw-spatial-CUDA-implementation-recovery-v2/`.
The public runner is `scripts/check_raw_spatial_features.py`; it schedules no
production training. CUDA admission is52GiB, allocator cap16GiB, runtime floor
32GB, with the original30-minute bound. Current V124 stays in the same worker;
no process was stopped, restarted or signaled to perform the brief check.

Independent CPU/NumPy auditing reopens all four16/18-step checkpoint files and
checks526,838,384 saved values for finiteness, steps/counts and nonzero learned
projection, without constructing a model, calling a neural module, drawing
noise, updating an optimizer or initializing CUDA. It verifies current neural
source matches the executed CUDA bytes and preserves the original CPU-source
scope. This does not independently repeat initial neural forward/encoder
identity checks; those remain the executed worker evidence.

The feature suites pass48 cases in28.00s; the new feature/tiling suites pass32
in4.37s, with19 shared spatial cases, for61 unique passing cases. Independent
NumPy dense attention and coordinate-group averaging check softmax masks and
partition geometry. Other checks cover tiny/rectangular fields, all-CFA constant
behavior, channels-last parity, gradients, learned reload and invalid options.
The earlier Ruff complaint about a test dict constructor was corrected without
changing its semantics. Final Ruff and whitespace checks pass.

Published `docs/raw-spatial-features.md`, updated current research/model/data
pages and preserved the earlier frequency result's meaning. The prepared90781/29
cohort now has implementation-check use only, with no production quality result.
All original catalogues, dataset membership and existing model receipts keep
their bytes. The implementation report is
`docs/results/raw-spatial-implementation-v1.json`; independent state/source audit
is retained in `.cache/current-quality-20261023-v1/raw-spatial-final-review-v1/`.

Publication verification checks327 local links,120 unchanged active V124
input/source/config bindings and the unchanged V120 selector. It verifies the
exact V124 worker2025028/create1793101753.04 remains live. An initial read-only
verification attempt treated that plan's frozen-file mapping as a list and
stopped before writing a receipt; the corrected check verifies all120 entries.
A diagram-label correction preserves the prepublication document/proof bytes
in the review cache. No neural receipt changed.

A matched trained quality trial is still required before drawing conclusions
about faint photographic or real GFX recovery. It should compare a fresh
control and spatial branch on identical90781/29 inputs, document actual gains
and weaknesses directly, and include native exact-GT triplets plus both GFX
pairs. Current V124/V125 training continues independently; quality remains
more important than speed. Broad SOTA and100MP/10s remain unproven, so the full
goal stays active.
