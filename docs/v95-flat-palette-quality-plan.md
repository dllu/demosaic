# V95 follow-up: preserve weak detail while improving saturated fields

The [V93–V95 review](v43-curated-original20k-review.md) finds clear photographic
and weak-detail gains, with saturated high-noise color errors and uncertain
unseen-camera gains still preventing promotion. Keep V43 as the working reference
and continue quality work with its architecture. This is a prospective training
comparison; it has no new held-out quality result yet.

## Matched comparison

| Arm | Initialization | Colored flat-field palette | Stage |
| --- | --- | --- | --- |
| V96 control | Final V95 20k EMA | Existing `flat_chroma_stops: 0` | 4,000 updates |
| V97 treatment | Same final V95 EMA | Existing `flat_chroma_stops: 8` | 4,000 updates |

Both use the original V43 architecture, curated 88,484-source Commons training
membership, seed 57, batch 16, native 256-pixel crops, BF16 training, fresh
optimizer/EMA, learning rate 1e-5 and 100 warmup steps. Preserve 25% paired /
25% native / 50% Commons, zero optical PSFs, `.15` weak textures and `.25`
photographic contrast attenuation. Validation/test and the GFX scene/siblings
remain outside training. No speed work or architecture change is included.

Within Commons, keep 10% smooth fields, 15% weak procedural detail, 5% other
procedural content and 70% photographs. Half of smooth fields stay neutral.
The treatment widens only the colored fields: maximum channel ratio rises
from 5 to 256, retaining the existing neutral fields, generator random draws
and geometry. Mean intensity is preserved before clamping; bright channels can
clip, so post-clamp means need not match. This changes 1,618 of the planned
64,000 clean patches, about 2.53%, without displacing photographic or weak-detail
draws. Poisson draws in affected mixed batches can differ; per-step seeding
isolates later steps. Paired/native inputs must match across arms.

The [earlier V59/V60 palette study](wide-flat-palette-full4k-review.md) improved
some saturated fields in a different architecture but did not justify promotion.
Its transfer to V95 is unproven. The current numerical package already contains
this palette option; no new image generator or loss is added.

## Execution and evidence

Use `scripts/train_v95_palette_trial.py` to freeze inputs/source and run discarded
24-update CPU/native32/B1 and CUDA/native256/B16 checks for both arms before
production. The actual 256-sample clean-data audit reads the curated cache:
171 photographic, 48 weak, 5 other procedural, 20 colored flat and 12 neutral
flat draws. Only the 20 colored draws change. In 1,000 paired smooth-generator
draws, random states match and all 512 neutral fields are exact. These data
checks and the 23 focused tests establish routing behavior, not model quality.

The first CPU invocation caught an omitted CLI version allowance and exited
with argparse status 2 before training. Its frozen plan/logs remain in
`.cache/quality-first-20261020/V95-palette-matched-training-v1/`.
The corrected explicit launch uses fresh namespaces:

- Plan/code/logs: `.cache/quality-first-20261020/V95-palette-matched-training-v2/`
- Checkpoints: `/mnt/external/demosaic/v95-palette-training-20261021-v2/`

All four actual preflights pass: 96 training/DINO forwards and 96 optimizer
updates. An independent CPU-only read checks each saved state's 71 finite
model tensors, 71 finite EMA tensors and 69 finite Adam states at step 24,
the exact V95 initializer and effective architecture. CPU and CUDA each have
12 identical shared paired/native observations; affected Commons observations
change as expected. The numerical package hash remains the completed V95
package. V96 production has been observed through step 25 with finite loss
and gradients; V97 follows serially. Full training and quality results remain
pending. The [preflight and live-launch receipt](results/v95-palette-preflights-and-training-launch-v1.json)
contains exact plan/source/checkpoint hashes, exited proof owners and actual
production owner/resource readings. Forty focused data/lineage/resource tests
pass; none is a held-out quality measurement.

The controller records actual resource readings every two seconds. Require
48 GiB available RAM and 64/384 GiB free on root/external storage, stable for
60 seconds before launch. During work, the RAM floor is 24 GiB; disk-only
shortages suspend the owned process group and resume the same worker after
the original launch thresholds recover. Waits are bounded, with no automatic
retry. Only this study's processes/artifacts are managed.

The initializer is the final V95 EMA checkpoint, SHA-256
`189f5530ef8be6384e101e00fe50ece19297436b0c65b5bb3cabbb2f327e2bb6`;
its full initialized model hash is
`8c8646e5e984148338748423fbb97b36143b9d14b494b8f7844520c282c826f3`.
Intermediate 1k/2k/3k checkpoints are diagnostic; final 4k EMAs are primary.
Independent saved-state checks and held-out review remain necessary.

## Quality decision

Evaluate V43, V95 and both final 4k endpoints together using fresh IEEE FP32
on the fixed full 427-photo panel, known/unseen camera panels, weak carriers,
neutral/saturated flats, and the standing GFX scene plus highlights. Keep
RawNIND's input-only global/channel gain adapters and common observations.
Require exact checkpoint stage/initializer lineage: V43 step 2k, V95 stage 20k
from V43, and V96/V97 stage 4k from V95. The evaluation driver supports these
explicit per-checkpoint expectations without changing the earlier study's gates.

Judge color tails alongside low-contrast detail and source/scene uncertainty;
a better photographic mean alone is insufficient. Publish at least two small
native noisy/restored/GT triplets per model with common coordinates/display
and checkpoint/noise/exposure receipts. View the native pixels and retain
negative outcomes. The ISO100 GFX image remains a qualitative reference, not
exact GT or a scoring target. Engineering checks and training-validation scores
do not justify model promotion.
