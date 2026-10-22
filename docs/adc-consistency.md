# ADC-only consistency on the current V84 model

**An optional observed-site correction improves V84's ADC-only PSNR on four
selected natural-detail contexts by .359 dB on average.** It uses the same
learned weights and replaces only valid measured CFA channels. The existing
Malvar correction changes neighboring unmeasured channels too and is mixed on
these examples. These are a small diagnostic, with a full427/four-CFA CPU check
running separately. The current architectural baseline remains V84.

[Scores, source/weight hashes, implementation checks and viewed-image receipt](results/v84-adc-sites-pilot-and-implementation-v1.json).

## Native comparisons

![ADC-only bark, feathers, forest and fur: noisy, V84, Malvar correction, site-only correction and exact synthetic GT](images/adc-consistency/photo-comparison.png)

Every cell is an unchanged **160×160 native-pixel crop**. Open the PNG at 100%;
a browser may fit the whole board to its window. The
[12 source triplets and metadata](images/adc-consistency/manifest.json) record
source attribution, full checkpoint hash, common coordinates, noise and display.
All methods share identical noisy and exact synthetic GT pixels.

| Detail | V84 sRGB PSNR | V84 + Malvar | V84 + sites | Sites change, dB |
| --- | ---: | ---: | ---: | ---: |
| Pale bark | 34.603 | 34.223 | 35.007 | +.405 |
| White feathers | 41.826 | 42.232 | 42.302 | +.476 |
| Forest canopy | 36.436 | 36.289 | 36.728 | +.293 |
| Gray fur | 42.055 | 42.110 | 42.320 | +.265 |

Site-only SSIM and gradient error improve in all four; chroma error worsens in
three. Malvar's mean PSNR change is −.016dB. The native outputs look close, and
bark/canopy remain softer than GT. This is a useful numerical gain with a color
tradeoff, not a demonstrated large visual improvement or a real-camera gain.

The four contexts were selected by viewing clean inputs before these outputs;
this correction was investigated afterward. They are the same sources and
observations as the [natural-detail gallery](heldout-detail.md), with RGGB,
shot=read=0, WB=[2,1,1.5], the shared camera matrix and display exposure ×1.
Context size is256; numerical ROI is[8,8,240,240], display ROI[48,48,160,160].
Scores use unquantized FP32 camera RGB rendered to sRGB. This condition includes
ADC quantization and demosaicing, with no simulated shot/read noise.

Four constant gray/magenta counterchecks show small spatial-uniformity tradeoffs.
The maximum channel's centered192×192 RMS, in normalized16-bit camera-RGB codes:

| Flat target | V84 | Malvar | Sites |
| --- | ---: | ---: | ---: |
| Gray .02 | .139 | .121 | .177 |
| Magenta .02 | .714 | .400 | 2.063 |
| Gray .18 | 1.520 | .866 | 1.324 |
| Magenta .18 | 3.403 | 2.888 | 3.199 |

These are normalized16-bit units, not the camera's14-bit ADC units. Ordinary
RGB8 previews look flat. Centered RMS measures spatial variation; it does not
establish a periodic CFA-grid artifact. Flat previews use ×4 at level.02 and ×1
at level.18, identically across methods.

## Implementation and use

`model.adc_cfa_projection` remains false by default. When enabled,
`model.adc_cfa_projection_mode` selects `malvar` (the backward-compatible
default) or `sites`. The site mode directly writes measured RGB values for
packed observations strictly between1/65535 and1−1/65535. Every other FP32
channel, including censored near-black/clipped sites, remains bit-identical.
It uses no target, fitted gain or output clamp and changes no learned tensors.

The model activates either operator **only for explicitly supplied shot=read=0**.
Any positive shot or read prior bypasses it, including mixed-profile batches.
It therefore does not improve the noisy ISO6400 GFX test or substitute for the
current reduced-blur/fine-detail training work. Real captures retain their
measured/estimated positive-noise conditioning.

Export a separate optional checkpoint from V84's final EMA:

```bash
source scripts/env.sh
uv run --no-sync python scripts/export_adc_cfa_projection.py \
  /mnt/external/demosaic/models/v84-original20000.pt \
  --expected-sha256 134887e12357aabf420cceee3ee53fc8832cf02a8f81ff883b829a9e51e16f10 \
  --mode sites --output /mnt/external/demosaic/V84-ADC-sites-new-export
```

The exporter refuses an existing output directory. The current generated
checkpoint is `/mnt/external/demosaic/V84-ADC-sites-export-20261022-v1/model.pt`,
SHA256 `c129262a40faf76c1acc236697eaf1dd7d12a0ee62603c2c47cccbe99cdd9da9`.
Its91 learned tensors independently match the original V84 EMA bit for bit;
only the serialized inference policy changes. The gallery above uses the
original checkpoint plus postprocessing. Actual exported-model inference
reproduces all four site scores and native PNGs exactly. All12 original V84
scores/PNGs also reproduce, and eight positive-noise outputs bypass bit-exactly.

Focused projection/export tests:31 passed. Related RGB, stabilization,
packing, inference and checkpoint tests:66 passed. Tests cover all four CFAs,
shared/per-image CFA indices, censored endpoints, exact channel values and
gradients, FP32 under CPU BF16 autocast, mixed noise profiles, older checkpoints
and mode round trips. Ruff passed for the six changed code/test files.
Active training/evaluation copies remain unchanged.

## Scope and credits

The separate full427 study evaluates all four CFAs, using one original V84
prediction and the two fixed operators on the same observation. It has no
training updates and does not replace the seven-condition photographic score
in the [current model table](current-model.md). Its plan is
`.cache/current-quality-20261022-v1/V84-ADC-full427-CPU-v1/plan.json`.

Sources and licenses are the same as the [natural-detail credits](heldout-detail.md#image-credits):
bark ©2007 Derek Ramsey (Ram-Man), CC BY-SA2.5; snowy egret by Serebit,
CC BY-SA4.0; Yakushima forest by Grendelkhan, CC BY-SA4.0; raccoon by Korall,
CC BY3.0. Triplet sidecars preserve full source URLs and license URLs. Modifications
include binning, cropping, simulated observation and restoration.
