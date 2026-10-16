# DINOv3 ConvNeXt feature-pyramid candidate

An optional reconstruction branch now uses genuine frozen DINOv3 ConvNeXt-Tiny
features at multiple CNN resolutions. It is engineering preparation, not a
trained quality result. The original fresh no-context/ViT-S/ViT-B arms are
[continuing to 10,000 updates](fresh-dino-capacity-10k.md) in their own frozen
worktree; this candidate does not change that experiment.

The [official model card](https://huggingface.co/facebook/dinov3-convnext-tiny-pretrain-lvd1689m)
identifies ConvNeXt-Tiny as a DINOv3 model distilled from ViT-7B. Its pinned
[configuration](https://huggingface.co/facebook/dinov3-convnext-tiny-pretrain-lvd1689m/blob/10d30274b4d445111e2d5bf75ac93bbd94db274b/config.json)
has four stages, widths 96/192/384/768 and depths 3/3/9/3. The installed official
Transformers implementation exposes stage maps at quarter through 1/32 input
resolution. Our genuine rectangular CPU probe verifies their shapes and finite
values. This suggests a way to test finer feature grids than our current
16-pixel-token bottleneck branch; it does not establish better demosaicing.

## Weights and implementation

[Availability and identity receipt](results/dino-convnext-tiny-availability-v1.json):

- Repository `facebook/dinov3-convnext-tiny-pretrain-lvd1689m`, revision
  `10d30274b4d445111e2d5bf75ac93bbd94db274b`.
- 111,299,216-byte safetensors file, SHA256
  `bd30a9459d6149564ef53af6e8a1999980953b009b94cde836ac1bac4d339cb2`,
  matching the Hub LFS identity.
- 27,820,128 frozen parameters. No random-weight fallback. The downloaded
  license is byte-identical to the existing [DINOv3 license](../third_party/dinov3/LICENSE.md).
  This project acknowledges Meta's DINOv3 materials; this is an independent
  restoration head, not an official Meta demosaicing model.

Select `model.dino_feature_fusion: convnext-pyramid` alongside `dino: true`
and the pinned ConvNeXt model/revision. The default remains `bottleneck`.
This option requires native-resolution pretrained-RGB restoration and rejects
packed processing, a ViT encoder, input adapters and query/value LoRA. Existing
checkpoints missing the new configuration field use the original branch.

Each frozen stage receives a learned 1×1 projection to 64 channels. Coarser
features are bilinearly upsampled 2× and added top-down. The first three levels
receive a 3×3 smoothing convolution, a channel projection and an independent
zero-initialized per-channel gate:

| Pyramid level | Native encoder grid | CNN offset grid | CNN channels |
| --- | --- | --- | ---: |
| First, including coarser context | 1/4 | 1/2 | 128 |
| Second, including coarser context | 1/8 | 1/4 | 256 |
| Third, including fourth-stage context | 1/16 | 1/8 | 512 |
| Fourth | 1/32 | Top-down context only | — |

The two earlier offsets enter after their encoder downsampling operations and
feed both subsequent computation and skip connections. The third enters the
original bottleneck. There are 262,336 trainable context parameters and 32,904,704
trainable parameters in the complete candidate; the corresponding no-context
model has 32,642,368. Backbone, fusion placement and adapter capacity change
together, so a future comparison will not isolate backbone capacity alone.

The preview retains the current ordinary camera/WB rendering, ImageNet channel
normalization and aspect ratio. It is padded on the bottom/right to 32 pixels
for the encoder. Each output is upsampled in that padded coordinate system and
then cropped to the CNN's 8-pixel padded extent. Directly resizing the whole
padded map to a smaller rectangle would distort its coordinates. Feature
upsampling does not create additional measured image resolution.

The frozen backbone stays in eval mode under no-grad. Autograd trains all
lateral/smoothing/output projections and gates. The CFA, generalized-Anscombe
conditioning, native FP32 head/tail and reconstruction losses remain as before.
Earlier offsets are cast to the corresponding hidden tensor's dtype before
addition, preserving the control's BF16/FP16 skip arithmetic at initialization;
small sub-ULP offsets can consequently round away. Prepared arms explicitly
retain `rgb_middle_skip_fp32: true` for matched bottleneck arithmetic.

Construction preserves global CPU RNG and common initial tensors. Portable
checkpoints omit the pretrained encoder but include every learned pyramid
tensor. Missing learned state fails loading. Existing default trunks receive
their original call signature.

## Engineering validation and proposed experiment

The [CPU engineering receipt](results/dino-convnext-pyramid-cpu-validation.json)
records the actual complete-suite and genuine-weight checks. These are separate
from CUDA validation, throughput and trained quality. The complete suite passes
488 tests with eight CUDA checks skipped in 96.74 seconds. Unit fixtures cover
common weights/global RNG, exact initial CPU BF16 predictions and common
gradients, frozen/eval encoder state, two-update feature gradients, padding
coordinates, fusion placement and nonzero portable-state/missing-state checks.

The genuine-weight preflight finishes successfully with the verified Gaussian
RGB prior and frozen ConvNeXt weights. Four CFA/rectangular/mixed-noise cases are
initially exact in FP32; a native 32px GBRG case is exact under explicitly
asserted CPU BF16. An actual native 256px Commons observation is initially exact
in FP32. Two discarded batch-one FP32 updates per arm use the same observations;
all three gates receive gradients immediately and all four lateral projections
receive them on update two. Encoder tensors stay byte-identical. Learned gate
norms are .001665/.002278/.003092, and native-256px FP32 portable reload is exact.
That initial preflight did not test full-size CPU BF16 training or a complete
optimizer/EMA/RNG restart.

The later [genuine-weight actual-trainer restart audit](results/dino-convnext-pyramid-cpu-restart.json)
now verifies a four-update CPU FP32 prefix against an interruption after two
updates followed by two resumed updates. It retains seed 48 and the original
10,000-update/100-warmup LR schedule, all frozen manifests and domain proportions,
while using batch one, native 64px patches and zero data workers. Both Commons
updates precede the interruption; native RAW and paired RAW follow it.

All 91 portable model tensors, 91 EMA tensors, 89 AdamW parameter states,
model configuration, best-validation scalar, Python/Torch RNG and empty CPU-only
CUDA RNG states match exactly. All four logged observations and numerical
training metrics match; only elapsed time is excluded. Genuine Gaussian and
ConvNeXt identities are checked, and the learned gates are nonzero. This closes
the CPU complete-state restart item in the earlier receipt. It does not prove
production batch-16/native-256px CUDA or BF16 continuation equivalence.

Reproduce the discarded audit independently with a new output directory:

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 HF_HUB_OFFLINE=1 \
  uv run --no-sync python scripts/audit_dino_pyramid_restart.py \
  --output /mnt/external/demosaic/benchmarks/dino-convnext-pyramid-restart-cpu-new
```

The first preflight used
the project's precision helper, which intentionally leaves CPU work in FP32;
its BF16 labels were incorrect. Its private receipt remains with a correction.
The explicit full-size second attempt was stopped in its own CPU process before
completion because of its cost. Only the completed third run is cited above;
it explicitly requests CPU autocast for the small fixture and asserts actual
convolution dtypes. No CUDA context was initialized by these preflights.

The [prepared V58 configuration](../configs/dino-convnext-pyramid-fresh-b16-v58.yaml)
starts from the verified Gaussian RGB prior, with fresh AdamW/EMA, seed 48,
batch 16, LR 1e-4, 100 warmup updates and the original 10,000-update schedule.
Commons 40,170, native 128, original paired 32, domain proportions,
4×→geometry/PSF→area2 and original 8× validation match the existing fresh
comparison. It includes no
weak-source, input-adapter, expanded-paired or new ADC-policy intervention.

Before launch, finish and review the running long comparison, verify its owner's
exit, run the complete CUDA-enabled test suite and the genuine-weight
CUDA/FP16/native-256px batch-16 checks. The
[prepared CUDA preflight](../scripts/preflight_dino_pyramid_cuda.py) checks initial
FP32/BF16/FP16 equality against no-context, two discarded Commons updates,
frozen-encoder identity, portable EMA FP16 predictions, exact model/EMA/AdamW/RNG
restoration before continuation, and a third native-RAW update. Its constant
preflight LR is 1e-4; this is not scheduled V58 training. It does not assert
bitwise equal CUDA optimization after continuation. Its peak allocation includes
both the original and restored models and is not a batch-size benchmark.

Only this script's live-owner rejection has executed: controller 164667 was
confirmed live, so the attempt stopped before CUDA initialization or output
creation. The model/gradient/state path is still unexecuted. It requires the
preceding controller/status files and the completed published review's path and
SHA256; its review must cover the original 10,000-update workflow. That prevents
preflight from overlapping the owned comparison or bypassing its review.

Batch 16 is the established
current-trunk setting; it is not a measured ConvNeXt throughput optimum. A
1,000-update first gate would retain the 10,000-step LR schedule. Require matched
logged observations and numerical development/full-427 results, analytic weak
texture/flats, native exact-GT triplets and the standing full GFX scene including
foliage/fence. All three cached additional-camera examples should also be
reviewed. ISO 100 and comparator outputs remain accurately labeled references.

One seed and source-bootstrap intervals cannot quantify training variability;
the [unchanged-control replay](control-replay-v57-review.md) demonstrates that
limitation. No inference-speed, convergence, SOTA or model-promotion claim is
made by preparing this branch.

## Isolated source for the next validation

The candidate now has a clean detached checkout at
`.cache/dino-convnext-v58-worktree`, commit
`797cfc852d2010c30f877cff1277e6c96103ccfc`.
[Actual source/import/input/guard receipt](results/dino-convnext-pyramid-frozen-source.json).
The sparse checkout retains code, configs, tests, licenses and result receipts,
without copying the report-image collection. Its production files match the
completed CPU restart audit exactly. Frozen manifests, genuine ConvNeXt files
and the Gaussian initializer verify their pinned hashes.

Two local directory aliases bind the standing GFX pair and three additional
camera captures to the existing main-repository cache. All five files verify
their source hashes and share the same cached inodes. No RAW copy, source-disk
access, decoding or permission change is needed for this setup.

An actual masked-CPU invocation from this checkout verifies that the model and
preflight imports resolve inside it. The CUDA preflight rejects still-live
controller 164667 before creating its proposed output or initializing CUDA.
The candidate's training run directory has not been created. This establishes
source/import readiness only; the GPU model/gradient/state path remains untested.

Use the shared existing environment with an explicit import path for later
validation, after the original comparison and manual review finish:

```bash
# Begin in the main repository so cache variables use its existing caches.
source scripts/env.sh
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
export PYTHONPATH="$PWD/.cache/dino-convnext-v58-worktree/src"
cd .cache/dino-convnext-v58-worktree
```

The complete CUDA-enabled tests and genuine CUDA preflight must run against
this checkout before a source/config/data/weight/review-pinned training launch.
No GPU work or training is queued automatically by freezing this source.
