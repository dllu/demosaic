# V157: a direct multiscale RGB residual for broad error and weak detail

V157 tests whether a spatial RGB path can remove broad parent error while
retaining fine, low-contrast detail. [V156](local-excess-risk.md) reduced added
quiet-neighbor error, but broad colored mottle and missing real cab crossings
remain. Its spectral proposal removes affine and very low frequency modes
before support and overlap. Those later operations can mix frequencies, so
coarse output is not literally frozen; there is still no unrestricted coarse
prediction path.

The new implementation and 45 CPU tests pass. CUDA compatibility checks cover
28 archived contexts, and genuine 8+2 model/EMA/Adam/RNG restoration passes.
Both fixed 1,000-update heads are running. Final restoration quality and actual
native viewing remain pending. This is a research implementation, with no
change to the general inference recommendation.

## What the new path predicts

[LateSpatialRgbDetail](../src/demosaic/late_spatial_rgb.py) combines two paths
fed by the same supplied frozen V143 camera RGB and observed RAW:

```text
output = V143 RGB + learned spectral correction + direct spatial RGB correction
```

The spectral estimator is the unchanged relative-phase model. The new path
uses four packed-grid scales at strides 1, 2, 4 and 8, width 24, seven residual
blocks, average downsampling, bilinear upsampling, additive skips and global
context at the coarsest scale. A zero final convolution predicts all twelve
C-major RGB phases, then pixel shuffle restores native RGB coordinates. This
path has no affine removal, spectral band, support gate, Malvar-only color
subspace or learned amplitude bound. It can represent DC and unsampled-color
corrections. Replicated CNN borders use slices with deterministic CUDA backward.

Its 39 input channels contain twelve centered parent-RGB phases, four signed
RAW-minus-parent CFA innovations, four physical variance coordinates, twelve
CFA-placement indicators, three parent means, three white-balance coordinates
and one noise-unit coordinate. Signal coordinates use `asinh`; the inherited
16-DN16 floor sets feature units. Image-wide parent means retain brightness
information after centering. No clean target or reference enters forward.

Image-wide shot/read RMS supplies the output amplitude unit. Exactly zero
physical variance makes the new path exactly zero. The inherited spectral
estimator still runs, including its own ADC behavior. This preserves ADC routing
under the noisy-only training protocol; it does not claim improved ADC quality.
Positive-noise outputs can predict either sign at any RGB phase. Neither the
noise units nor the network output are calibrated confidence or a safety bound.

The zero final layer exactly embeds the unchanged estimator at initialization.
All shared spectral weights initialize identically, then both paths train
jointly. The new path adds 83,964 parameters / 32 tensors: total **117,677 / 45**
versus **33,713 / 13** for the control. This tests the complete hybrid, with
greater capacity and compute; it is not a parameter-matched ablation. Global
gradient clipping also couples the two paths' optimizer pressure.

The supplied V143 parent already uses official frozen DINOv3 ConvNeXt-Small
features. This experiment reuses its cached outputs, without a new parent or
DINO pass. It is an independently implemented packed-grid residual, not a
reproduction of the restoration papers in the [research notes](research.md).

## Fixed comparison

The [recipe](../configs/quality-v143-spatial-rgb-v157.yaml) fixes two fresh heads:

| Arm | Architecture | Supervision |
| --- | --- | --- |
| `local-control` | Unchanged relative spectral estimator | Exact V156 local-regret recipe |
| `spatial-rgb` | Same estimator plus direct multiscale RGB path | Same objective and coefficients |

Both use the same 1,000 cached V148 batches / 4,000 old observations. There are
882 supervised batches and 118 ADC batches with zero total gradient. All 1,000
AdamW and EMA clocks advance, including momentum/decay coasting. Pixel and
gradient penalties, delivered-RGB spectral MSE coefficient .25, local-regret
weight 1, domain weights, noise conditions, geometry, initialization of shared
weights, LR schedule and clipping remain fixed. Local regret compares actual
32px/hop16 RGB error against the original V143 parent, using exact training
targets only in the loss. It permits beneficial denoising of an incorrect parent.

The control must reproduce V156's complete local-risk trace, raw/EMA/Adam states
and all 1,644 reviewed outputs bitwise. There is one fixed architecture and two
final raw/EMA endpoints per arm, with no quality-selected width, scale or early
checkpoint. The new architecture can alter both spectral and spatial parameters;
any quality change cannot be attributed to the spatial output alone.

All 86 previous neural files remain byte-identical; one new module is added.
There are no new data constructions, noise draws, parent/DINO calls, original
lookups, RAW decodes or `/mnt/dataz` accesses. Protected GFX captures, JPEGs and
siblings remain excluded from training and original media remains read-only.

## Readiness evidence and live work

The [preparation publication](results/v157-spatial-rgb-preparation-v1.json)
retains actual receipts and frozen sources. The nine new tests independently
enumerate NumPy feature coordinates, verify all four CFA embeddings, exercise
DC and missing-color capacity, exact zero-variance routing, broad-error learning,
finite earlier-layer gradients and the initial identity derivative. Together
with the 36 local/delivered objective tests, **45 tests pass in 1.80s**. Tests
establish these implementation properties, not real-photo quality.

CUDA compatibility uses 84 actual evaluations: current control, frozen V156
control and zero-spatial extension on each of 28 native 256/384/512/768 contexts.
All outputs match archived V156 arrays exactly, including four CFAs and protected
real controls. Two discarded ten-update runs include actual save at update 8
and model/EMA/Adam/RNG restoration before the remaining two updates. Production
starts fresh. All 58 parameter tensors receive finite nonzero gradients over
the prefix; all 58 Adam states are finite at update 10. Four strict CPU model/EMA
loads and exact restored control raw/EMA/Adam against V156 pass.

The immutable readiness snapshot records 122 completed production rows, each
with an exact V156 control trace match, and three owners actually observed live
by PID and creation time. This is a historical prefix, not a final count or an
endpoint. The new branch has larger early gradient norms and invokes clipping;
no quality gain is inferred from training losses or state checks.

The final review is queued behind the original controller. Mandatory strict CPU
checks of the actual final checkpoint, all 58 Adam states, four exports and exact
control states/trace precede review claims. Frozen postprocessors preflight the
actual dynamic metric, reviewer and renderer imports before queuing.

The new study budgets retain **88 GiB local / 200 GiB external** free space,
with a further .5 GiB projected margin before launch. These are new budgets;
previous study policies, arrays and machine receipts remain unchanged. Each new
raw/EMA prediction collection needs 2.211 GiB on local/external SSDs. Controls
are evaluated afresh, compared bitwise and only then reuse archived storage.
No evidence is deleted or moved. RAM guards remain 52 GiB at launch / 32 GiB
at runtime, with a 12 GiB CUDA quota.

## Required quality review

All four fixed endpoints use the same 822 cached inputs: **3,288 actual head
evaluations**. Actual mesh-blank error, mixed quiet spatial/DC error, native512
noisy-flat full/coarse error, weak natural detail, ADC photos and sloped fields
remain separate. The score/audit design expects 4,686 rows, independent NumPy64
and Decimal checks, and 30 unscored real rows. This reused adaptive cohort is
not blind validation or a guarantee against hallucination.

The planned 72 native figures retain the previous 48 boards and 24 repeated-cell
triplets: two mesh, two noisy-flat and two quiet ROIs for every endpoint. Each
160×160 crop keeps its original pixels, coordinates and method display transform.
The final manifest must bind source/ROI, checkpoint hash, noise conditions and
exposure. Repeated cells add no observations. Actual viewing must follow rendering.

The standing DSCF3879 ISO6400 / DSCF3880 ISO100 scene includes sky, building,
foliage and coarse fence. DSCF3842 / DSCF3835 retains both fine-cab windows,
both noise priors and both SOOC JPEGs. Aperture, shutter and motion differ in
these independent references: they are qualitative references, **not exact GT**,
and will not be pixelwise scored. A lower added correction alone does not prove
cleaner fields; visible wires and actual output-versus-target error both matter.

[Local-time diary](../diary/2026-11-03-21-20-55-v157-spatial-rgb.md) ·
[Preparation verification](results/v157-spatial-rgb-preparation-verification-v1.json).
