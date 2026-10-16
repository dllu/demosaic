# Fresh no-context versus DINO-S at 10,000 updates

Both original schedules are complete. The two models remain visually close on
the fixed GFX crops, and both still lose fine fabric cords in the exact-GT
example. These six examples do not establish a broad DINO benefit or justify
replacing V43 in the README. [All ten new native PNGs, hashes and provenance](results/fresh-none-S10k-cpu-review.json).

This is a small **CPU FP32 qualitative check** while DINO-B continues training.
It restores four cached 512×512 GFX contexts and two previously serialized
256×256 synthetic observations. It does not produce a full-frame output,
full-suite score or speed result. The [original matched trial](fresh-dino-capacity-10k.md)
still requires B and the complete numerical/native/analytic/full-frame review.

## Matched training and inputs

Both models use seed 48, batch 16, original 10,000-update cosine schedule, genuine
Gaussian CNN initialization, fixed Commons 40,170/native 128/original paired 32,
4×→geometry/PSF→area2 training, and the same physical/noise policies. Their
original training source bundle is
`2f1a2251d8141d335e99266343b46b61b8da3cb13012fc63d79ea5c3968ad01c`.
All **403 logged step/domain/observation hashes match exactly**. The common
effective model configuration and listed training fields were checked before
inference. Both AdamW states reached 10,000 with final LR 1e-5; the
[S boundary receipt](results/fresh-dino-capacity-S10k-boundary.json) also records
finite logged losses/gradient norms/model tensors and a nonzero context gate.

The models differ in frozen DINO features and trainable projection capacity.
One training seed and the existing nondeterministic CUDA execution policy do
not isolate semantic-feature quality or estimate training-repeat uncertainty.
The check uses EMA weights:

| Arm | Whole-checkpoint SHA256 |
| --- | --- |
| No context | `0df4ff404c38b8f4b42f6451486e91c97631544b1c817c126f371195942f3af4` |
| DINO-S | `ae74bc17012c85d5253f24da4dbaaec4486ed430aa143d852442754288d56bad` |

DINO-S uses genuine `facebook/dinov3-vits16-pretrain-lvd1689m`, pinned revision
`114c1379950215c8b35dfcd4e90a5c251dde0d32`. Both models enable the explicit
FP32 middle skip. The immutable evaluation snapshots are recorded in the
receipt; the active controller's expected final model paths were not created
early.

## Standing GFX scene

The source remains cached DSCF3879 (ISO6400, f/1.7, 1/240s) versus DSCF3880
(ISO100, f/5.6, 3s), with the original source hashes and predeclared regions in
the [standing selection](../configs/gfx-qualitative-20231231.json) and
[preceding CPU report](gfx-none10k-cpu-context-review.md). This execution reads
their saved linear observations rather than decoding either RAW again.
The scene and siblings stay out of training; originals remain read-only.

The ISO100 capture is independently AHD demosaiced and calibrated against its
own CFA measurements. It is **not exact GT**: aperture, motion and a 3m38s time
gap limit the comparison. No warping or pixelwise ISO100 quality score is used.
All methods share the same noisy-camera WB/matrix, shot
`.0014635775921166604`, read variance `1.0715704128646712e-6`, and display
exposure ×4 (+2EV). Every panel is an unresized native 160×160 crop.

Primary rows read **noisy → DINO-S 10k → ISO100 reference (not GT)**:

![Foliage: noisy, DINO-S and approximate ISO100 reference](images/fresh-none-S10k-cpu-foliage-S.png)

![Fence: noisy, DINO-S and approximate ISO100 reference](images/fresh-none-S10k-cpu-chain-link-fence-S.png)

Both models preserve broad leaf shapes but soften fine texture. Both retain
continuous mesh lines. Small local fence differences do not establish an
overall winner. These direct rows read **noisy → no-context 10k → DINO-S 10k**;
neither learned panel is GT. Display pixels are copied exactly from the primary
outputs, without new rendering or adjustment:

![Direct foliage comparison](images/fresh-none-S10k-cpu-foliage-direct.png)

![Direct fence comparison](images/fresh-none-S10k-cpu-chain-link-fence-direct.png)

The sky outputs look close and remove most visible grain. Fine building
bracket/truss detail remains softened:

![Direct sky comparison](images/fresh-none-S10k-cpu-overcast-sky-direct.png)

![Direct building comparison](images/fresh-none-S10k-cpu-building-detail-direct.png)

The [sky](images/fresh-none-S10k-cpu-overcast-sky-S.png) and
[building](images/fresh-none-S10k-cpu-building-detail-S.png) primary triplets
and all coordinates are also retained in the receipt.

## Two exact-GT examples

These are the same two fixed 8×-binned Commons sources and CPU-generated noisy
observations as the [preceding review](cross-camera-none10k-cpu-review.md).
The target is exact for this simulated degradation, rather than a real RAW
reference. No new noise draw or source decoding occurs. Both models use RGGB,
shot `.00256`, read variance `.0000262144`, 16-bit ADC with black `.03`,
WB [2,1,1.5], the common evaluation matrix and display exposure ×1.
The receipt records source/cache/serialized-observation hashes, the 256px source
tile, 160px ROI and full display transforms. These two cases are illustrative;
they are not the full 427 evaluation or a model-selection mean.

Fabric, noisy → DINO-S 10k → exact simulated GT:

![Fabric: noisy, DINO-S and exact simulated GT](images/fresh-none-S10k-cpu-example-fabric-S.png)

The same observation with no-context 10k, reused unchanged:

![Fabric: noisy, no-context and exact simulated GT](images/none10k-cpu-example-fabric-none10k.png)

Both miss the fine cords and differ from the target's fabric color.

Building, noisy → DINO-S 10k → exact simulated GT:

![Building: noisy, DINO-S and exact simulated GT](images/fresh-none-S10k-cpu-example-building-S.png)

The same observation with no-context 10k, reused unchanged:

![Building: noisy, no-context and exact simulated GT](images/none10k-cpu-example-building-none10k.png)

Both produce clean architectural edges while losing cloud detail. The common
inputs and display avoid attributing a noise-draw or exposure difference to
the models, but these examples still cannot establish broad quality.

Sources: [Roy Egloff](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg)
and [Dietmar Rabich](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified by
binning, cropping, camera/noise simulation and restoration. Derived photographs
retain that license. GFX photographs belong to the project owner and are used
with permission.

## Execution checks

All ten new PNGs and the two reused no-context exact-GT triplets were visually
inspected. Ten PNGs pass hash, RGB/geometry and native-panel checks; all four
saved float32 GFX predictions pass hash/shape/dtype/finite checks. Rerendering
those predictions reproduces their displayed pixels byte exactly. Every shared
noisy/reference panel and all direct-comparison pixels match their parents
exactly. Synthetic noisy/GT panels also rerender exactly from the saved
observations. The two new synthetic restored float arrays were not separately
saved, so their restoration panels have no independent float rerender audit.

The replay archives its production source and checkpoint snapshot; the artifact
audit/publication driver is archived alongside them. No CUDA context was
initialized. Production code and the live workflow's frozen training/evaluation
files are unchanged. Actual CPU inference, artifact checks and Ruff pass.

After sourcing `scripts/env.sh`, replay using the receipt's immutable S snapshot:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=4 HF_HUB_OFFLINE=1 \
  uv run --no-sync python scripts/replay_fresh_dino_10k_cpu.py \
  /mnt/external/demosaic/evaluation/fresh-none-S10k-cached-cpu-v1/weights/weights-ae74bc17012c85d5253f24da4dbaaec4486ed430aa143d852442754288d56bad.pt \
  --output /mnt/external/demosaic/evaluation/fresh-none-S10k-cpu-replay
```

The cached baseline report and serialized observations are required. Complete
the original B schedule and full matched review before choosing a new model.
