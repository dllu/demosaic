# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, frozen DINOv3 features and tiled 16-bit output on NVIDIA GB10.
**V120 Small is the general recommendation**: full 427-photo mean 37.04008 dB,
measured known/unseen-CFA means 54.31272/54.00872 dB, tested ADC maximum 55.52 DN16.
It uses a pretrained DRUNet trunk and the official DINOv3 ConvNeXt-Small pyramid.
[Primary results](docs/v120-v121-primary.md) · [Current choices](docs/current-model.md).

| Useful choice | Measured strength | Remaining limits |
| --- | --- | --- |
| V120 Small | Broad photo/camera results and complete 102MP RGB16 checks | Fine foliage, mesh, neon and dark-field mottling |
| V114 Tiny | Lower tested ADC maximum, 51.73 DN16 | Camera/photo tradeoffs; [comparison](docs/current-model.md) |
| V1435k + optional `detail` | Stronger measured periodic detail under both GFX mesh priors | Partial orientations, support seams, boundary spill and slow correction; broad superiority unproven |

The [supported-amplitude option](docs/supported-wave-amplitude.md) raises fresh
mesh response **26.4%** and lowers image RMS **1.0%** versus `cross`. All256 absent
neural cases and64 new natural photo controls retain their parents. Mean/worst
added blank RMS rises42.1/28.4%; response reaches only **7.1% of exact procedural
GT**. The `detail` mode is the default inside explicitly enabled `--phase-harmonic`;
ordinary inference keeps the stage off. Partial orientations, support seams,
boundary spill, nonperiodic texture and slow correction remain unresolved.

[Completed V153](docs/delivered-spectral-objective.md) moves spectral loss onto
delivered output: mesh response rises6.04–7.97% over matched control to2.45–2.59%
of GT, with worse actual blank errors, natural response and ADC photos.
[V151](docs/noisy-objective-training.md)/[V152](docs/relative-phase-estimator.md)
retain quieter controls, while [V150](docs/objective-floor-training.md) gives
about3.06% lower ADC-photo RMS. Real fine cab crossings remain missing.
[Architecture and loss comparisons](docs/current-model.md#quality-and-remaining-work)
retain the complete measured strengths, failures and independent evidence.

[Completed V154](docs/robust-spectral-objective.md) gives weak spectral errors
more relative pressure. Native512 noisy-flat RMS falls **0.45–0.50%** versus
V143, with slightly lower actual blank errors. Broad mottle remains, mesh and
natural detail weaken, and quiet regions beside structure get **1.51–2.27% worse**.
All six endpoints,96 native figures and independent audits are complete.

The [matched V155 parent comparison](docs/matched-parent-comparison.md) finds
V120's coarse noisy-flat error1.59–2.36% lower than V143, but total noisy-flat
RMS2.31–5.11% higher and worse ADC slopes. Neither restores the fine cab fence.
All1,644 fresh paired outputs,64 native figures and independent audits are complete.

[Completed V156](docs/local-excess-risk.md) lowers mean quiet-region RMS **0.30–0.63%**
versus matched MSE; all 32 mixed controls improve at both endpoints. It retains
5.59–10.52% more mesh response than V143, with less response than MSE. Broad mottle
and missing cab crossings remain. All four endpoints,72 native figures and
independent audits are complete; local regret becomes the next learned-head
training control, with stronger mesh/standalone-flat/ADC comparators retained.

The [active V157 trial](docs/spatial-rgb-residual.md) adds a direct multiscale RGB
path to address coarse parent mottle and missing-color detail. CPU/CUDA readiness
passes; both fixed heads are training and restoration quality remains unmeasured.

Training uses freely licensed images, geometry before downsampling and zero
optical blur. The prepared bank has 90,773 photos and 37 reviewed regions.
[Source review](docs/current-source-loss-review.md) · [Data pipeline](docs/training-pipeline.md) ·
[V143 training results](docs/v143-final5000-quality.md) · [Research and prior experiments](docs/research.md) ·
[PSNR history](docs/performance-history.md) · [Historical diary](diary/index.md).

## Current 100% crops

Noisy → V1435k with `detail` → exact procedural GT. This native 160×160 crop
uses the first active source and largest added RMS on a fixed 160 grid,
chosen after evaluation. All columns share 8× camera-linear contrast about the
exact empty field, then WB/matrix/+3EV. Pixels are not resized.
[Central diagnostics, failure views and complete metadata](docs/images/supported-wave-amplitude-v1/manifest.json).

![Native noisy, detail amplitude and exact GT with shared eightfold contrast](docs/images/supported-wave-amplitude-v1/mesh-seed2026112302-present-iso6400-prior-RGGB-retained-contrast8-triplet.png)

Noisy → V143 + V153 delivered-mosaic raw → **exact constructed GT**, two fixed
mesh crops. Mean response rises17.40% over V143 (7.97% over matched control),
but reaches only2.59% of GT and crossings remain missing. Actual blank and
quiet-region errors worsen. Native160×160 cells, ROI `[176,176,160,160]` in512px
RGGB contexts, shot .00128/read6.5536e-6, common exposure8 and contrast1;
no crop-pixel resizing.
[All endpoints, checkpoint/source hashes and display metadata](docs/delivered-spectral-objective.md).

![Mesh2302: noisy, V153 delivered-mosaic restoration, exact constructed GT](docs/images/v153-delivered-objective-v1/comparison-00-delivered-mosaic-raw-step1000-triplet.png)

![Mesh2309: noisy, V153 delivered-mosaic restoration, exact constructed GT](docs/images/v153-delivered-objective-v1/comparison-02-delivered-mosaic-raw-step1000-triplet.png)

V156's small quiet-neighbor gain: noisy → **local-risk EMA** → exact constructed
GT, ISO6400 and ISO12800 priors. Broad colored mottle remains; these crops do not
show a clean-field solution. Native 160×160 cells in 512px RGGB contexts,
ROI `[80,176,160,160]`, common exposure 8 and 40× camera-linear contrast about the
exact quiet target. Shot/read variance parameters are .00128/6.5536e-6 and
.00256/2.62144e-5; crop pixels are never resized.
[All methods, checkpoint/source hashes and display metadata](docs/local-excess-risk.md).

![ISO6400 quiet: noisy, V156 local-risk EMA, exact constructed GT](docs/images/v156-local-risk-v1/comparison-26-local-risk-EMA-step1000-triplet.png)

![ISO12800 quiet: noisy, V156 local-risk EMA, exact constructed GT](docs/images/v156-local-risk-v1/comparison-28-local-risk-EMA-step1000-triplet.png)

V154 retains the stronger standalone-flat gain:
[ISO6400](docs/images/v154-robust-spectral-v1/flat-iso6400-charb-0p01-EMA-step1000-triplet.png)
and [ISO12800](docs/images/v154-robust-spectral-v1/flat-iso12800-charb-0p01-EMA-step1000-triplet.png)
native triplets use exact constructed GT; [full conditioning/display details](docs/robust-spectral-objective.md).

V150's stronger ADC-only result remains useful: mean photo RMS falls 3.06% on
two held-out sources/four CFAs. Native
[bark](docs/images/v150-objective-floor-v1/comparison-42-floor16-matrix-EMA-step1000-triplet.png) and
[fur](docs/images/v150-objective-floor-v1/comparison-43-floor16-matrix-EMA-step1000-triplet.png)
triplets retain exact constructed GT; [noise, licensing and display details](docs/objective-floor-training.md).

Noisy organic texture remains weak: [current feather/grass/bark views](docs/delivered-spectral-objective.md)
and the [earlier native photo gallery](docs/spatial-photo-supplement.md).

Standing real GFX100S scene: DSCF3879 ISO6400 → **V120 Small, historical Haar
prior** → DSCF3880 ISO100 f/5.6. Complete 102MP outputs, native 160px cells, common
+2EV. The independent ISO100 exposure is a qualitative reference, **not exact GT**;
aperture, exposure and motion differ. Foliage remains painterly.
[GFX gallery](docs/gfx-qualitative.md) · [Camera comparisons](docs/native-camera-development.md).

![V120 GFX foliage: noisy, restored, independent ISO100 reference](docs/images/v120-v121-fixed-Haar-GFX-v1/V120-foliage-fixed-Haar-triplet.png)

![V120 GFX fence: noisy, restored, independent ISO100 reference](docs/images/v120-v121-fixed-Haar-GFX-v1/V120-chain-link-fence-fixed-Haar-triplet.png)

Fine green mesh beside the red train's cab: noisy → V143 → sparse → wide → cross →
**detail** → ISO6400 JPEG → independent ISO100 AHD → ISO100 JPEG. Complete 102MP
outputs, nearby fixed prior, native 160px cells, common +4EV. Both ISO100 views
are **not GT**; aperture, exposure time and processing differ. Stronger crossing
contrast remains soft and uneven. The tested 2.88MP sky keeps every parent value.
[Both priors, standing scene and failure controls](docs/supported-wave-amplitude.md).

![Complete-frame fine green mesh, identical native crops](docs/images/supported-wave-amplitude-v1/mesh-nearby-Haar-mesh-profile3879-fine-green-mesh-left-JPEG.png)

![Complete-frame fine green mesh, identical native crops](docs/images/supported-wave-amplitude-v1/mesh-nearby-Haar-mesh-profile3879-fine-green-mesh-right-JPEG.png)

The [stronger RawNIND full-frame reference](docs/rawnind-fullframe.md) and
[Q2/Sony/GFX50R comparisons](docs/cross-camera-qualitative.md) show other limits.
Broad state-of-the-art quality and 100MP within 10 seconds remain project goals.

## Setup and inference

Linux, Python 3.12+, `uv` and a CUDA 13-compatible NVIDIA driver are required for
the lockfile. DINOv3 requires approved Hugging Face access through `HF_TOKEN`.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic infer /mnt/external/demosaic/models/v120-final20000.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff \
  --shot 0.001 --read 0.000001 \
  --tile 512 --overlap 64 --batch-size 4 --precision float32 --cudnn-benchmark
PYTHONPATH=.:src:scripts uv run pytest -q
```

`--phase-harmonic --phase-harmonic-envelope detail` restores contrast inside
reciprocal support. Use `cross` for lower tested blank RMS. The stage remains
opt-in, with `detail` its default; [tradeoffs and complete native comparisons](docs/supported-wave-amplitude.md).

Noise values are examples; use suitable camera/input priors.
Use `--phase-harmonic` to enable Detail, or
`--phase-harmonic --phase-harmonic-envelope edge` for the earlier stage.
[Usage and all explicit modes](docs/usage.md) retain the earlier comparisons.
[Linear DNG + full-resolution JPEG batch export](docs/dng-export.md) preserves
camera RGB and adapts existing darktable XMP edits. Add `--hot-pixels` to repair
isolated Bayer defects before restoration.
`--hot-pixel-clusters` also handles paired same-color defects; see the
[native crop investigation](docs/hot-pixel-clusters.md).
[Usage](docs/usage.md) · [current training](docs/quality-first-training.md) ·
[data pipeline](docs/training-pipeline.md) · [experiments](docs/experiments.md) ·
[documentation guide](docs/index.md). Quality takes priority. State-of-the-art
quality and 100MP within 10s remain project goals; full-frame timing is
checkpoint-specific.
