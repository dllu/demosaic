# Crossed thin lines with matched empty backgrounds

**An optional procedural source now supplies weak crossed lines and empty
backgrounds.** It is implemented in the actual training reader and remains off
by default. The [completed V1421k review](v142-crossed-line-pilot.md) gains
.05212dB faint ADC PSNR and lowers noisy-flat spatial RMS4.55% versus V129.
Selected weak grass/wood bands improve, but mesh remains weak; coarse noisy
error stays5.08% above V120 and selected ADC-only DC bias worsens. Retain this
useful source for further quality trials. V141's frozen loss trial is unchanged.
[Sources, tests and target inspection](results/crossed-line-training-data-v1.json) ·
[Actual V142 setup and fixed review](results/v142-crossed-line-setup-v1.json).

The previous weak generator provides band-limited fields and curved fibers.
This source adds two crossing families of thin wires, without copying any test
capture or fitting its geometry. Periods span6–32 final sensor pixels, wire
sigma.4–1.2px and family separation35–145°. Level spans2⁻¹⁰–2⁻¹ and requested
peak relative contrast.005–.2,relative to the sampled level; channel tint changes per-channel
contrast. Neutral and chromatic positive/negative line
contrasts vary independently of presence. Backgrounds are constant or gently
affine, with random colors.

Presence is sampled with probability.5. The generator also supports explicit
present/empty counterfactuals with identical geometry/background parameters and
RNG consumption. A compact visibility mask leaves exactly empty areas even
inside a present example. The masked detail has approximately zero mean within
FP32 precision, so an overall color shift does not identify the present target.
Negligible Gaussian tails are not amplified when no wire crosses a small mask.

Targets stay scene-linear FP32, evaluated on the2× augmentation canvas before
the existing geometry and final area2 reduction. No8-bit rasterization, camera
noise, Bayer sampling or display transform is introduced by the generator;
the ordinary training degradation applies afterwards. No optical PSF is added.

## Native target inspection

Each cell below is an unchanged160px crop after the actual geometry/area2 path:
empty background → present target → target detail amplified10× for inspection.
Both first cells share a source-level display exposure, recorded in the
[manifest](images/crossed-line-training-data-v1/manifest.json). The third cell's
contrast boost is display-only. These are procedural training targets, **not
noisy/restored/GT model-performance comparisons**.

![Very faint crossed-line target and empty background](images/crossed-line-training-data-v1/seed-2-training-pair.png)

![Dark crossed-line target with an empty surrounding region](images/crossed-line-training-data-v1/seed-43-training-pair.png)

All six examples were viewed, including faint positive/negative and chromatic
patterns. The data inspection establishes sensible generated targets, not that
a trained model will recover real mesh or avoid false texture.

## What the actual V142 schedule contains

The1k schedule contains7,632 Commons slots, including773 crossed-line source
reads:397 present and376 absent, out of16,000 total target slots. A replay
through the frozen actual reader matches all12 logged crossed-line source
recipes in its saved trace prefix. Every absent read matches its empty
counterfactual exactly. [Completed production](results/v142-completed-reader-trace-v1.json)
now verifies all1,000 updates and all30 final logged mesh recipes; the source
audit retains its earlier scheduled-count observation unchanged.

For present examples after geometry/area2, median exact-empty area is61.59%
(interquartile50.73–69.39%). Median detail RGB RMS divided by the sampled
brightness is.526%, with interquartile.185–1.340%. Sampled brightness median
is.02637, range.000979–.49661. The new fine structure therefore occupies a small
part of the overall training support. This audit does not show that its weight
is sufficient or that a model can recover it under noise. Values precede
camera transport and random training exposure.
[All773 reads, counterfactual statistics and exact trace bindings](results/v142-crossed-line-source-coverage-v1.json).

The [completed mesh-power supplement](results/v142-mesh-peaks-v1.json) keeps
the two windows and all10 noisy-input-only peaks from the earlier
[measured-green diagnostic](green-phase-spectrum.md). It compares saved
V120/V129/V141/V142 outputs without further inference or RAW/noise generation.
Explicit DFT checks720 complex coefficients across40 rows, maximum power
difference3.02e−14; the original control-only preflight remains preserved. Saved-output/noisy-input power ratios are
**descriptive, not correct-detail gains or quality scores**; actual native
comparison and exact-flat error remain necessary.

## Reader and compatibility

```yaml
weak_texture_fraction: 0.15
fine_weak_texture_fraction: 0.0
mesh_texture_fraction: 0.10
augmentation_downsample: 2
optical_blur_probability: 0.0
```

The mesh and existing fine-texture fractions must fit inside the weak-texture
quota. Thus this example replaces part of the existing synthetic component;
it does not expand total procedural probability. About half the new draws are
empty backgrounds. Existing photographs, reviewed regions, smooth fields and
unselected procedural draws retain their previous pixel values. Validation
always disables this source. The effective mesh fraction is serialized; a changed
fraction rejects before constructing a resumed model. Initializing a fresh run
from the same parent remains supported.

The44-test data/regression suite checks independent NumPy64 construction,
background/mean/presence behavior, continuous precision and RNG preservation,
exact unchanged routing outside the replaced subquota, validation exclusion,
quota bounds and actual training with an asserted crossed-line reader target. A
two-step run exactly matches1+1 resumed model/EMA/Adam states; changed-fraction
resume rejects before model construction. Some tests
overlap the gradient-loss suite;44 is this suite's count, not additional unique
loss tests.

The [prepared V142 recipe](../configs/quality-v120-crossed-line-pilot-v142.yaml)
keeps V129's V120 parent,cohort,seed70,quota.5,zeroPSF,B16/native256/BF16,
LR1e−5,warm100 and1k budget. It keeps pixel/gradient epsilon.0003, independently
of V141's tested loss change. CPU/CUDA16+2 pass, including exact native/paired
clean/noisy hashes versus V129 and genuine changed-fraction resume rejection.
Fresh1k production and fixed102-input native/faint/GFX/48-flat reviews are
complete, with84 published native boards and independent checks. The endpoint
binder requires complete finite training state, exact frozen source and matched
non-Commons inputs, with10 tests rejecting substituted inputs/schedules.
V129's newly retained48 flat controls can be reused. Both protected GFX pairs,
their JPEGs and siblings remain out of training.

[Generator](../src/demosaic/textures.py) · [Reader](../src/demosaic/data.py) ·
[Tests](../tests/test_crossed_line_textures.py) ·
[Gallery driver](../scripts/report_crossed_line_training_examples.py).
