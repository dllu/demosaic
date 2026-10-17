# Completed matched normalization study: V68/V69

Both original4k schedules and the full review are complete. V69 gains+.02032dB
photo sRGB PSNR over matched control, but its own1k progress interval includes
zero. Weak texture/coarse color and mixed real/bright-color behavior prevent
promotion. V43 remains the working reference. No extension beyond4k is queued.

[Final performance report and decision](normalization-v68-v69-original4k-review.md).
[All81 actually viewed native triplets](normalization-v68-v69-original4k-native-gallery.md).
[Full statistics, metadata and audits](results/normalization-v68-v69-original4k-review.json).
[Earlier first1k review](normalization-v68-v69-first1k-review.md).

## Frozen matched recipes

| Setting | V68 control | V69 augmented |
| --- | --- | --- |
| Training normalization | Full-context statistics | Stateless half-probability center-half statistics per image |
| Initializer | V63 original20k EMA | Same |
| Initial optimizer/EMA | Fresh AdamW/EMA | Same |
| Planned horizon / review gate |4,000 /1,000|Same|
| Seed / LR / warmup |50 /3e−6 /100|Same|
| Batch / native patch / precision |16 /256 /BF16|Same|
| Workers Commons / paired / native |4 /2 /2|Same|
| Commons / native / paired |40,170 /128 captures /32 pairs|Same|
| Domain fractions |25% paired /25% native /50% Commons-procedural|Same|
| Data path |4×→geometry/PSF→area2, original noise/ADC/wide8 palette|Same|
| Ordinary inference |Original full-context normalization|Same|

Only policy/run/notes differ between the [control recipe](../configs/dino-convnext-normalization-control-b16-v68.yaml)
and [augmented recipe](../configs/dino-convnext-normalization-augmented-b16-v69.yaml).
The new larger quarantined corpus is unused. Parent V63 was selected using
prior results, a research choice rather than blind selection. Its checkpoint is
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
Training source bundle:
`db5fb3ba42827e9db043dbc85f069bb1e5568cdafa872f7340d872852bc6a771`.
This is fresh fine-tuning from parent EMA; the closed20k optimizer is not resumed.

## Genuine CUDA checks and first1k gate

[Executed preflight, independent audit and launch](results/normalization-augmentation-CUDA-and-launch.json).
The [preflight operator](../scripts/preflight_normalization_cuda.py) performs six
production-size discarded updates each for control, augmentation and3+3 resumed
augmentation:18 genuine CUDA updates, native256/B16/BF16/workers4+2+2 and actual
data across all domains. It verifies exact pre-fetch model/optimizer/RNG and
pre-update EMA restoration;91/91/89 finite saved states;89 finite trainable
gradients; mixed per-image masks and identical logged input/domain/LR fields.
DINO remains genuine/frozen/gradient-free with unchanged hash
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.

The four-CFA mixed-mask physical CUDA fixture matches its CPU oracle within the
predeclared3e−6 bounds; the zero-mask path is bitwise default and preserves RAW,
canvas and RNG. Ordinary FP16 EMA loading matches manually restored EMA outputs
exactly on two fixed photos. The independent CPU artifact reader rechecks
inputs/source bundles, states/masks and full/resumed RNG/config. CUDA optimization
is not bitwise deterministic: full-versus-resumed maximum model/EMA differences
2.38e−7/1.64e−7 are observations, not a quality gate. Peak CUDA allocation7.213GB
is not total unified RAM. These checks do not establish trained quality.

Both production arms stop at the original1k gate on the4k LR curve; all41 logged
input/domain/LR rows match. Immutable1k checkpoints:

- V68: `456a5fb245bc807d91470cbb067e137ea48ace8eb5796a3d6ad9218573d9ad0c`.
- V69: `6f34be8b2cc4fbba1116b4ed17bbafe41d5526da928238d194b6355b9b8b665c`.

The completed1k review includes all81 actual native views. Its mixed small gains
lead to the explicit decision to complete the original4k horizon, not promotion.
Original failed1k wrappers/audit attempts remain recorded in its receipt.
[Coordinate diagnosis and implementation](normalization-augmentation.md).

## Completed original4k continuation

[Actual launch/restoration](results/normalization-original4k-continuation-launch.json).
[Control completion and augmented handoff](results/normalization-original4k-control-complete-handoff.json).
[Both original4k boundaries and independent log read](results/normalization-original4k-training-completion.json).
Both arms resume complete model/EMA/Adam/RNG state from1k into separate output
run directories. Only the run path changes; original1k logs/checkpoints/review
remain unchanged. The4k LR curve, source/data/seed and policies are exact.
Production read-only hooks verify actual model/all89 Adam and all three RNG
families before first data fetch; EMA is checked before its first EMA update,
after the first optimizer step. DINO before/after hashes remain exact.

The initial continuation wrapper lacked the spawn-worker main guard and made
zero updates. Only its exact owned stalled trainer group was stopped; the failed
status/logs/run directories remain intact. Fresh v2 directories use the corrected
main guard, verified by actual CPU import under`__mp_main__` without training,
file writes or CUDA initialization. No checkpoint/data/numerical bound changes.

Both4k trainers and controller have exited. Frozen boundaries verify finite
91 model/91 EMA/89 Adam, complete RNG,89 changed model/EMA tensors from1k,
exact context buffers, source/data/recipe/parent and model config. All162 logged
steps/domains/LRs/batch fingerprints match independently across arms. The extra
step1001 row records the resumed start. Every augmented mask is SHAKE256-checked;
losses/gradient norms are finite; validation is at1k/2k/3k/4k.183 frozen guards
and original1k log prefixes pass. No unlogged fingerprint claim is made.

Immutable4k checkpoints:

- V68: `5bcb45adb6ace6aed3cd2071ad56f36bd019645ec4c117c4d6f65beda220b737`.
- V69: `8162020f954426a9fb5f657eb3e7d74ec7cde65c5c58f1f369ee556d0d535e59`.

Training archive/status:
`/mnt/external/demosaic/benchmarks/normalization-v68-v69-original4k-continuation-v2/`
and `/mnt/external/demosaic/runs/normalization-v68-v69-original4k-continuation-v2.json`.
Controller622973/1792260581.40 and final trainer658410/1792262498.98 are historical
identities; both exited. Producer package remains frozen in the earlier first1k
workflow's`work/` directory; that folder name does not change the actual4k step.

## Completed full4k review

[Actual frozen queue and engineering replay](results/normalization-original4k-review-queue.json).
The review released only after both original4k boundaries and actual training
owner exit. The completed-boundary reader checks checkpoint hashes,162-row logs,
restoration receipts and all training guards. Live/partial/failed/wrong-step
states cannot release inference. Thirty focused tests and Ruff pass. The actual
historical1k engineering replay reproduces36 statistics and24 zero self-comparisons,
fifteen witnesses, with no inference; it is not a fabricated4k result.

The shared-source parent/control/augmentation review completes432 known/540
unseen/74,424 full427 cases,1,792 analytic cases, three full GFX outputs/six
RGB16 TIFFs,18 other-camera crops and96 selected CPU-color predictions. Sixty
comparisons/fifteen witnesses include six own1k progress pairs. The frozen427/
418/416 source cohorts give45 photographic sensitivities. Hue completes2,352
fresh candidate predictions and reuses2,352 strictly verified same-source
parent/released-reference arrays; no source exception. Case/group audits verify
28,224 metric fields and864 group scalars. Independent state/artifact checks
verify57 primary PNGs,29 F32 arrays and six RGB16 files. All supplementary and
source-sensitivity audits pass. Inputs use existing local RAW caches.

All81 required new original PNGs were actually viewed at100%, separately from
prior1k views. All26 groups share identical noisy/reference pixels and source/
ROI/noise/display/WB/matrix metadata. The report contains two exact-GT photographic
triplets per model and GFX foliage/fence alongside sky/building. Four historical
V43 README originals are additional context; shared preview pixels are exact,
model/source/training histories differ. The model alias's canonical path and
hash match the retained V43 report. No model or pixel edit occurred in publication.

Completed review archive/status:
`/mnt/external/demosaic/benchmarks/normalization-v68-v69-original4k-review-workflow-v1/`
and `/mnt/external/demosaic/runs/normalization-v68-v69-original4k-review-workflow-v1.json`.
Review owner638004/1792261092.43 exited; its115 frozen guards remain verified.
The final manual receipt is under
`/mnt/external/demosaic/benchmarks/normalization-v68-v69-original4k-manual-review-v1/`.

This study is closed. V43 remains the working reference; no post4k extension or
production normalization-policy change is queued. The full PROMPT objectives of
SOTA, decisive real-photo superiority and100MP within10s remain unmet/unproven.
