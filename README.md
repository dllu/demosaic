# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, frozen DINOv3 context and tiled 16-bit output on NVIDIA GB10.

**V120 Small remains the general recommendation:** 37.04008 dB on 427 photos,
known/unseen-CFA means 54.31272/54.00872 dB and verified 102MP RGB16 exports.
It uses a pretrained DRUNet trunk and the official DINOv3 ConvNeXt-Small pyramid.
Fine foliage, mesh, neon and dark-field mottle remain weaknesses.
[Results](docs/v120-v121-primary.md) · [Current choices](docs/current-model.md).

The latest detail experiments retain useful tradeoffs: **V198 EMA reaches
11.158% of constructed-GT mesh amplitude**, with stronger real cab modulation,
but introduces green/magenta building fringes and false texture. V200 slightly
improves quiet/flat error while reducing mesh response to 11.102% of GT.
The [shared-edge training comparison](docs/shared-edge-comparison.md) adds small
quiet/flat gains but lowers EMA mesh response to 10.874%; the same fringes and
incomplete crossings persist.
V187 is quieter and V195 avoids those new building color failures in the
reviewed views. [Complete comparison](docs/scale-supported-cfa-wave-comparison.md) ·
[Seven-state native viewer](docs/images/v200-scale-supported-cfa-wave-v1/native-viewer.html).
Broad state-of-the-art quality and 100MP within 10 seconds remain goals.

[Weak-detail literature review and proposed experiments](docs/weak-detail-literature-2026-11.md)
examines the fence/flat-region tradeoff and recent methods. The first proposed
shared-edge trial and its [full quality review are complete](docs/shared-edge-comparison.md).
The [first withheld-CFA diagnostic](docs/withheld-cfa-evidence.md) shows why
independent sample agreement still needs an adequate edge/background model.
Its [geometry refinement](docs/withheld-cfa-edge-refinement.md) improves the
measured synthetic weak-direction/false-detail tradeoff.
The [completed three-noise wire panel](docs/edge-snr-ladder.md) still finds
strong direction imbalance: V200 EMA recovers 86.7% of the strong increment but
8.1% of the weaker increment far from the edge at the clearest tested prior.
A [competing-orientation selector](docs/competing-orientation-comparison.md)
improves one fixed mesh's weaker orientation sector from 28.41% to 33.55% at EMA,
but another weak sector worsens and overall mesh response falls to 10.607%.
The [completed fresh-noise review](docs/competing-edge-response.md) raises far-edge
weak response 3.13%→5.06% at the 1600 prior with slightly lower quiet error;
strong response falls. Both endpoints/all native boards are reviewed, with
persistent building/flat artifacts.
The [complementary stage](docs/complementary-comparison.md) retains frozen V200
EMA and adds proposals: full review finds almost unchanged weaker directions,
11.121% aggregate mesh amplitude and slightly higher quiet/flat error. Both
real-photo families retain their detail/color failures. The [three-noise review](docs/complementary-edge-response.md)
finds a small conditional gain at the clearest prior: far-edge weak response
8.14%→9.43%, with strong response retained and slightly lower quiet error.
A [coverage/response diagnostic](docs/complementary-coverage-quality.md) finds
low weak response even when a nearby carrier is present.
A [fixed-wave GT oracle](docs/measured-wave-oracle.md) raises response to 19.39%,
but quiet error worsens on 56/64 views and weak-increment error on 46/64;
target access does not supply a deployable detail improvement.
The [input-only local-support prototype](docs/local-validated-waves.md) improves
a two-geometry pilot's far response from 0.96% to 2.80% above V143, with quiet
RMS +0.43%; it reduces global-support cab ripples but still misses fine crossings.
The [complete three-prior panel](docs/local-wave-full-panel.md) finds far-edge
weak response 1.826%→2.690% at400, with quiet/increment RMS +0.405%/+0.289%.
Local support lowers global-support error in all six cells; gains remain
source-dependent and higher-noise weak detail stays missing.
A [three-harmonic follow-up](docs/local-wave-shapes.md) reaches 5.46% far weak
response but raises quiet/increment error and adds building color bands;
one harmonic remains the default. The independent fold-assignment fix is retained.
[Individual harmonic validation](docs/individual-wave-validation.md) lowers
far error versus H3 group support, with response 4.07%; building bands persist.
The [phase-aligned measurement average](docs/phase-measurement-aggregation.md)
raises the fixed pilot's400/far weak response2.80%→12.68% versus matched H1,
with quiet/increment error+5.44%/+1.94% and severe building bands. Both projection
arms are fully reviewed. An [A-only neural background diagnostic](docs/withheld-neural-background.md)
predicts withheld building/cab RAW better than the analytic fit, supporting a
richer nuisance test. Its [completed matched correction pilot](docs/neural-nuisance-reconstruction.md)
reduces added building/quiet error but loses400/far weak recovery3.69%→0.90%;
both cab profiles still miss fine crossings. Native comparisons and all controls
are retained. [Holding its analytic proposals fixed](docs/neural-nuisance-fixed-proposals.md)
recovers2.69% weak response, with quiet/increment RMS−0.57%/−0.13% versus
conditional analytic H1, which retains3.69% response. Building banding is much
smaller; missing crossings remain unresolved.
The [full-model RAW-attention comparison](docs/raw-spatial-continuation.md) has
completed its **V131 control**: [targeted native review](docs/v131-endpoint-quality.md)
finds faint-ADC +0.146 dB across four sources, with fur/grass/wood gains and a
bark regression. Ordinary/shadow gains are about 0.02 dB; fine cab crossings and
soft foliage remain unresolved. The experimental `v131` preset is available.
V132's added-attention arm is training. Its [matched1k review](docs/v132-progress1000-quality.md)
gains0.034 dB faint ADC over V1311k but stays0.240 dB below V120, without clear
new real mesh recovery. The20k architecture comparison remains pending.
V131's [completed broad review](docs/v131-broad-primary.md) improves427-photo
PSNR by0.04000 dB (400/427 source gains), with unseen-camera −0.04381 dB and
worst ADC mean-color error1,816 DN16 versus V120's55.5. Its small high-noise
weak-amplitude gain also raises weak-band error. The opt-in
[`v131-adc-malvar` variant](docs/v131-adc-projection.md) reduces the ADC color
maximum to20.0 DN16 and adds0.151 dB ADC-photo PSNR over V131, with weakest-band
error+1.43%. Positive-noise output is unchanged; fine real mesh remains unresolved.

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
```

Noise coefficients above are examples; use suitable camera/input priors.
The optional `--phase-harmonic` stage defaults to supported-amplitude detail;
`--phase-harmonic-envelope cross` has lower tested blank RMS.
[Tradeoffs](docs/supported-wave-amplitude.md) · [Usage](docs/usage.md) ·
[DNG/JPEG export](docs/dng-export.md) · [Hot-pixel repair](docs/hot-pixel-clusters.md).

## Development

Reusable data, losses, runtime, checkpoints and evaluation live in
`demosaic.experiments`; named model choices and composed wave stages live in
`demosaic.models`. New cached-head trials use explicit recipes and one runner.
Historical script entry points and frozen experiment evidence remain available.
[Architecture and workflow](docs/architecture.md) · [Current experiments](docs/experiments.md).

```bash
uv sync --extra dev --extra nonlocal
uv run demosaic-experiment models
uv run demosaic-experiment prepare configs/experiments/orientation-balanced.json \
  .cache/experiments/competing-new
uv run demosaic-experiment inspect .cache/experiments/competing-new
PYTHONPATH=.:src:scripts uv run pytest -q
```

The shared-edge cache, matched training and raw/EMA quality review are complete.
The same-data competing-orientation trial has also completed all 900 updates.
Preparation does not launch training. Training data comes from freely licensed
photos and procedural targets, with geometry before downsampling and zero
optical blur in the current recipes. [Data pipeline](docs/training-pipeline.md).

## Representative 100% crops

Noisy Malvar → **V120** → exact synthetic GT. Each cell is 160×160 unchanged
pixels; native256 RGGB context, ROI `[48,48,160,160]`, shot 0.00256/read
2.62144e−5, shared WB/matrix, exposure 1 and clipped sRGB display.
V120 checkpoint SHA256 `a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
[Source/ROI/display metadata](docs/images/v120-v121-primary-v1/manifest.json) ·
[Source credits and licenses](docs/v120-v121-primary.md#native-exact-gt-triplets).

![Bark: noisy, V120, exact synthetic GT](docs/images/v120-v121-primary-v1/crop-801b668c1c29105a.png)

![Fur: noisy, V120, exact synthetic GT](docs/images/v120-v121-primary-v1/crop-881399e7a68af49a.png)

The competing selector's [directional gain](docs/images/competing-orientation-v1/comparison-02.png)
and [counterexample](docs/images/competing-orientation-v1/comparison-06.png) are
noisy → competing EMA → exact constructed GT (native160, exposure 8/contrast 1;
[full provenance](docs/competing-orientation-comparison.md#the-directional-improvement-and-its-counterexample)).
The complementary lower-noise gain has [source0](docs/images/complementary-edge-response-v1/iso400-source0-far-triplet.png)
and [source1](docs/images/complementary-edge-response-v1/iso400-source1-far-triplet.png)
triplets with [full provenance](docs/complementary-edge-response.md#native-pixels-still-show-substantial-attenuation).

V131's completed continuation has native [bark](docs/images/v131-endpoint-v1/bark-small-triplet.png)
and [fur](docs/images/v131-endpoint-v1/raccoon-fur-small-triplet.png) noisy → V131 →
exact constructed-GT triplets at the same ordinary conditions above. Its faint
[fur gain](docs/images/v131-endpoint-v1/raccoon-fur-contrast0p025-adc-contrast20-comparison.png)
and [bark regression](docs/images/v131-endpoint-v1/bark-contrast0p025-adc-contrast20-comparison.png)
use common contrast20, ADC-only noise and unchanged native pixels.
[Checkpoint, source and display provenance](docs/v131-endpoint-quality.md).

The input-only local stage retains [source 0 without a weak gain](docs/images/local-validated-wave-pilot-v1/source0-far-role2-triplet.png)
and [source 1 with a gain](docs/images/local-validated-wave-pilot-v1/source1-far-role2-triplet.png):
noisy → local support above V143 → exact constructed GT, native160 cells,
exposure2/contrast1. [Complete parent/configuration/noise/source metadata](docs/local-validated-waves.md#native-triplets-retain-a-gain-and-a-counterexample).
The [completed full-panel gallery](docs/images/local-wave-full-panel-v1/native-viewer.html)
adds all eight sources and three priors, including a
[source1 gain](docs/images/local-wave-full-panel-v1/iso400-source1-far-triplet.png)
and [remaining source7 limitation](docs/images/local-wave-full-panel-v1/iso400-source7-far-triplet.png)
under the same native crop/display conditions.
The individual-harmonic trial retains native noisy → restored → exact-GT triplets for
[source0](docs/images/individual-wave-pilot-v1/individual/source0-far-role2-triplet.png)
and [source1](docs/images/individual-wave-pilot-v1/individual/source1-far-role2-triplet.png),
under those same conditions, alongside its
[persistent building-band failure](docs/images/individual-wave-pilot-v1/stress/building-prior-failure-ROI.png).
[Measured tradeoffs and configuration provenance](docs/individual-wave-validation.md).

The fixed-proposal neural-nuisance trial retains native noisy → restored →
exact-GT triplets for [source0](docs/images/neural-nuisance-fixed-v1/triplets/iso400-index0008-role2-triplet.png)
and source1 below, at ROI`[176,176,160,160]`, exposure2/contrast1 and
shot/read`8e-5/2.56e-8`. Fine crossings remain weak.
[Checkpoint/source metadata and measured costs](docs/neural-nuisance-fixed-proposals.md).

![Source1: noisy, fixed-proposal neural nuisance, exact constructed GT](docs/images/neural-nuisance-fixed-v1/triplets/iso400-index0024-role2-triplet.png)

The competing selector's [cab detail](docs/images/competing-orientation-v1/readme-cab.png)
and [building color failure](docs/images/competing-orientation-v1/readme-building.png)
are noisy → competing EMA → independent ISO100/AHD reference. They remain native160
pixels with matched coordinates/transforms; the separate real captures differ
in aperture, exposure and motion and are **not exact GT**.
[Complete source, checkpoint and display provenance](docs/results/competing-orientation-v1/representative-real.json).

[Documentation](docs/index.md) · [Experiment history](docs/history/experiments-through-v200.md) ·
[Diary](diary/index.md) · [Storage](docs/storage.md).
