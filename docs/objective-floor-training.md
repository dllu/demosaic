# V150 matched loss-floor trial

V150 tests a specific supervision change suggested by the completed
[gradient-allocation diagnostic](spectral-loss-allocation.md). Two identical
fresh native matrix heads train with 2 or 16 DN16 loss floors. **Trained quality
remains unmeasured.** Both discarded CUDA checks and the checkpoint 250 audit
pass; the fixed final review retains actual blank/quiet errors and adds ADC
photo and sloped-field controls.

| Setting | Native control | Candidate |
| --- | --- | --- |
| Component |31,409-parameter native complex matrix head|Identical|
| RGB loss standard-deviation floor |2/65535|16/65535|
| Spectral loss variance floor |(2/65535)²|(16/65535)²|
| Physical noise inputs / forward |Original packed RAW, variance, CFA, WB and supplied V143 parent|Identical|
| Data / horizon |1,000 cached B4 batches; 4,000 old observations; 1,000 fresh updates|Identical|
| Loss family |Original RGB pixel/gradient Charbonnier plus pre-gate spectral MSE|Identical|
| Optimizer / schedule |AdamW LR .001, warmup 50, clip 1, ramped EMA .999|Identical|

The larger floor reduces pressure from near-noiseless training examples. It
also changes absolute Charbonnier smoothing through the normalization units;
this is not simply a fixed multiplier of every RGB loss. It does not change
input noise, frequency features, support gates or an inference threshold. The
old peak-weighted and post-output alternatives remain diagnostics rather than
additional changes in this experiment. No noisy-flat or ADC safety guarantee
follows from the gradient result.
The native operator matches the diagnosed parameterization and complete archived
control; V149's [alignment gains and weaknesses](coherent-phase-estimator.md)
remain documented separately.

## Engineering and matched training

The [recipe](../configs/quality-v143-objective-floor-v150.yaml) adopts the complete
V148 cache. All input/target/parent arrays and batch fingerprints are checked
before both heads consume the same tensors. Source distribution, domain
weights, geometry, seed, horizon, clipping and EMA remain V147/V148/V149's.
Photographs retain native 256 contexts, procedures 512, with bin4→geometry→area2;
no photograph is stretched or tiled to simulate larger context. The inherited
90,782-photo/27-region eligibility and validation/protected-source exclusions
remain unchanged. The new ADC review controls are never training inputs.

All twelve initial parameter tensors match. Frequency outputs start zero and
preserve the parent exactly. The 85 neural source files are unchanged; the
candidate's explicit variance floor exists only in the training loss helper.
Eight new CPU tests cover all four CFAs and ADC/high-noise regimes: the helper
at 2 DN exactly reproduces the legacy value and coefficient gradient ; 16 DN
preserves the high-noise result and reduces the ADC spectral gradient by 64.
These tests passed in 1.10s.

Compatibility checks match the old trained native forward and archived pixels
exactly on 28 cases across 256/384/512/768 contexts and every CFA, using 56 actual
forward-function evaluations. Both fresh heads then complete ten discarded CUDA
updates, including genuine 8+2 model/EMA/Adam restoration. All 12 tensor gradients
are nonzero and finite, with 4.07 GiB peak allocated CUDA. Production starts
fresh. At checkpoint 250 all 24 Adam states and both raw/EMA states are finite;
the native control's raw/EMA/Adam state matches V149 exactly. The preparation
snapshot also checks the complete 423-row native control trace prefix exactly.
These are engineering checks, not quality improvements.

## Fixed ADC controls and full review

All four final raw/EMA 1k endpoints cover 822 cases: the retained 798 plus 24 ADC
controls. There is no early-epoch or loss-based endpoint selection. Most of this
cohort has already informed earlier research; it is not fresh independent
validation. The fixed 72 native figures comprise 48 boards and 24 repeated-cell
triplets, with identical source/ROI/display transforms across methods and no
crop-pixel resizing.

Eight added photographic ADC observations adopt two existing native 256 exact
synthetic targets—bark and raccoon fur—across four CFAs. The targets retain
their existing .025 contrast transform, source/licensing metadata, input bytes
and 16-bit ADC/black .03 settings. Source IDs
`0ae232278265dabbdd54f52c34045a3d03323aa7` and
`2b5a51667b9906eecead8f82e08c7ba11750f8c6` remain excluded from the training
manifests and all adopted training metadata. Two approximate binned camera
references in the older ADC study are not adopted here.

Sixteen new analytic camera-RGB affine-plane observations use native 512,
four fixed levels/tints/slopes and four CFAs each. Deterministic ADC construction
uses no Poisson or Gaussian draws. Independent long-double quantization checks
all 4,194,304 packed values; maximum FP32 representation difference is .001953
DN16. These have exact constructed array targets, not physical capture GT.
The noise variance input remains zero under the established ADC convention.

The 24 additional V143/DINO parent calls finish before training preparation,
with unchanged model/backbone hashes and RNG; peak allocated CUDA is .99 GiB.
Head training and endpoint review require zero new parent/DINO or noise calls.
The six new RGGB figure templates use native 160 cells. ADC photos use
ROI `[48,48,160,160]`, exposure 1, contrast 40. Planes use
ROI `[176,176,160,160]`, exposure `.18/level`, contrast 8 about common exact target
channel means. Other CFA placements remain in the numerical review.

The standing DSCF3879 ISO6400/DSCF3880 ISO100 scene retains sky, building,
foliage and chain-link crops. The DSCF3842/3835 cab mesh retains both windows,
both noise priors and both camera JPEGs. ISO100/AHD/JPEG references differ in
aperture, shutter, processing and motion: they remain **qualitative references,
not exact GT**, and are never pixelwise scored. All original captures/siblings
remain excluded from training. Only cached arrays are read; no RAW decoding,
original-media access or `/mnt/dataz` lookup occurs.

The reporting preflight passes 64 cached parent cases: 32 mixed quiet controls,
eight all-CFA present/absent meshes and all 24 added ADC controls. Independent
base/photo/blank/quiet/block formulas agree on 280 scalars, maximum 1.24e-13,
without CUDA initialization or any neural/noise call. The first harness tried
to import the frozen review by its original module name; it stopped at imports.
The corrected harness loads the actual frozen file path. Failed source/receipt
remain preserved; no reporter, model, input, endpoint or worker changed.

## Evidence and remaining work

The [preparation evidence](results/v150-objective-floor-preparation-v1.json)
preserves 13 byte-exact receipts, frozen sources, the two CUDA checks, cached ADC
parent evidence, the checkpoint 250 audit and the active 423-row snapshot. Both
heads and the queued full review are active at that snapshot. RAM/disk reserves
and the 12 GiB CUDA quota remain enforced. Original machine receipts and previous
quality comparisons remain unchanged.

Final 1k states, all endpoint arrays, independent scores and actual native viewing
are still required. The broader fine-detail/clean-sky goal remains active;
[current model choices](current-model.md) retain their existing quality evidence.
See the [local-time diary](../diary/2026-11-03-15-03-40-v150-objective-floor-trial.md).
