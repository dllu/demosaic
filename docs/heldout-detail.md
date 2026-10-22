# Natural fine-detail comparisons

**V101's final fine-detail continuation improves PSNR on all12 selected cases
versus both V84 and V100.** The gains are strongest at low noise and visible
changes are small. V84/V100/V101 all preserve substantially more bark grain,
feather texture, canopy structure and fur than RawNIND here. At high noise,
white plumage, distant trees and individual hairs remain smoothed.

The four contexts were selected by viewing clean inputs before inspecting
these model outputs. They cover mixed contrast, including weak fine structures;
they are not a set of globally low-contrast images. Their exact source IDs are
absent from the training cohort. This small diagnostic complements the
[full photographic and camera results](current-model.md). Both continuations
and their [full matched primary panels](v84-curated-quality-review.md) are complete.

Each cell is an unchanged **160×160 native-pixel crop** at the8×-binned evaluation
resolution. Open the original PNG at100%; a browser may fit the board to its
window. Columns share the same noisy observation, coordinates, display and exact
synthetic target. RawNIND uses input-only CFA-channel gain. V101 is highlighted
among the matched checkpoints in this gallery.

## Current continuations

V100/V101 each continue the exact V84 final20k EMA for10,000 updates on the
curated88,484-source cohort, with fresh AdamW/EMA. V100 retains the control
recipe; V101 removes optical PSFs and adds weak textures, photographic contrast
attenuation and reviewed fine-detail ROI sampling. Their comparison tests that
combined package, not a single isolated component.

| Condition, four-source mean | V84 PSNR | V100 PSNR | V101 PSNR | V101−V84, dB | V101−V100, dB |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADC-only | 38.730 | 38.806 | **38.885** | +.155 | +.079 |
| ISO100 prior | 40.244 | 40.305 | **40.354** | +.110 | +.048 |
| ISO12800 prior | 33.409 | 33.416 | **33.426** | +.017 | +.010 |

V101's PSNR/SSIM improve in all12 cases against both checkpoints. Gradient error
improves in12/12 versus V84 and11/12 versus V100; chroma improves in10/12 and9/12
respectively. The native images remain close. Slightly stronger low-noise bark
grain and canopy contrast are useful progress; high-noise detail remains a
quality target. These means describe four selected240-pixel interiors, not the
full427 benchmark or real-camera quality.
[Complete V101 per-case scores and viewed-image receipt](results/heldout-detail-V101-final-v1.json).
The planned final endpoints were used without searching intermediate checkpoints.
The [completed full photographic/camera comparison](v84-curated-quality-review.md)
confirms a smaller widespread photographic gain, with camera means close to V84.

All three learned checkpoints here retain their original output policy. The
[optional ADC-only site correction](adc-consistency.md) is evaluated separately;
it is not applied to any column in these training comparisons.

## Low noise

At the ISO 100 prior, V84 retains the fine pale bark texture, feather strands
and canopy detail that RawNIND softens:

![ISO100: noisy, V100, V101, V84, RawNIND and exact synthetic GT on bark, feathers, forest and fur](images/current-detail/iso100-prior/photo-comparison.png)

[ISO100 source triplets and metadata](images/current-detail/iso100-prior/manifest.json)
include source attribution, checkpoint hashes, source/context coordinates,
noise parameters and display exposure.

With no simulated shot/read noise, demosaicing and ADC quantization still
leave some fine-texture errors:

![ADC-only: noisy, V100, V101, V84, RawNIND and exact synthetic GT](images/current-detail/adc-only/photo-comparison.png)

[ADC-only source triplets and metadata](images/current-detail/adc-only/manifest.json).
The [optional ADC site correction](adc-consistency.md) gains .400dB across the
complete427-photo/four-CFA ADC-only panel with unchanged V84 weights. Its native
examples include these four contexts, preselected fabric/building views and
posthoc weakest-gain/chroma-increase cases. Color/uniformity tradeoffs remain
documented; positive-noise inputs bypass it.

## High noise

At the ISO 12800 prior, V84 restores the broad structures much better than
RawNIND, but the feather/canopy/fur examples show why detail retention remains
an active quality target:

![ISO12800: noisy, V100, V101, V84, RawNIND and exact synthetic GT](images/current-detail/iso12800-prior/photo-comparison.png)

[ISO12800 source triplets and metadata](images/current-detail/iso12800-prior/manifest.json).
The standing [GFX comparisons](gfx-qualitative.md) provide a separate check on
real ISO 6400 RAW data, including foliage and chain-link fencing.

## Inputs and reproduction

These are the original seed42 native256 contexts at indices124,200,320,392 of
the fixed full427 photographic validation panel. Sources use the existing
8× binned linear-sRGB caches. Display ROI is **[48,48,160,160]** within each
context; optional numerical scores use the **[8,8,240,240]** interior.
The [selection file](../configs/heldout-fine-detail-v1.json) records context
coordinates and hashes. Filtering and reindexing the dataset before extracting
these contexts would change the crops.

The three conditions use RGGB and the existing physical-noise protocol:

| Condition | Shot coefficient | Read variance | Display exposure |
| --- | ---: | ---: | ---: |
| ADC-only | 0 | 0 | ×1 |
| ISO100 prior | .00002 | .0000000016 | ×1 |
| ISO12800 prior | .00256 | .0000262144 | ×1 |

These are declared priors, not measured ISO calibrations. WB=[2,1,1.5] and the
shared camera-to-sRGB matrix come from [evaluation.yaml](../configs/evaluation.yaml).
Noisy previews use Malvar demosaicing. All methods use FP32 CPU inference on
the same 12 cached observations; the CPU noise draws are newly generated and
do not replace the original full-panel CUDA scores. Display uses the same
linear-to-sRGB transform and exposure across columns.

V84 selects the final20k EMA from checkpoint SHA256
`134887e12357aabf420cceee3ee53fc8832cf02a8f81ff883b829a9e51e16f10`.
RawNIND weights have SHA256
`c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0`.
The [reference receipt](results/heldout-detail-V84-reference-v1.json) binds the
input plan, complete numerical report, immutable reference boards and 24
source triplets. All 48 displayed cells were inspected at native resolution;
model and input hashes remained unchanged.
V100 uses its final10000 EMA, checkpoint SHA256
`4b689fb187b13df72fbf79ebd46f98cf7361c3ca8a97fb1f7afee940b249ad3e`.
Its receipt preserves the earlier three boards/60 native160 cells.
V101 uses the final10000 EMA, checkpoint SHA256
`6f691c653a618bdde0d7db501f3efc557a9699e2dbba73cf94c7440b364ef3e3`.
Its receipt adds12 triplets and records actual inspection of the current three
boards/72 native160 cells, with self-contained immutable gallery copies.
All shared noisy/GT pixels remain exact; earlier receipts and source crops are
unchanged. V101's local checkpoint is
`/mnt/external/demosaic/v84-curated-quality-20261022-v2/train/V101/last.pt`.

[report_heldout_detail.py](../scripts/report_heldout_detail.py) prepares shared
observations and evaluates additional checkpoints. The frozen local input plan
is `.cache/current-quality-20261022-v1/heldout-detail-inputs-v2/plan.json`.
Use its copied worker for comparisons so the numerical implementation stays
identical. This current gallery can grow when useful models appear; the
reference receipt preserves the original V84 evidence.

## Image credits

All panels are modified through binning, cropping, simulated observation and
restoration. Rows are ordered as follows:

| Detail | Original image and author | License |
| --- | --- | --- |
| Bark | [Kentucky Coffee-tree](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg), Photo (c)2007 Derek Ramsey (Ram-Man) | [CC BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5) |
| White feathers | [Snowy egret in profile](https://commons.wikimedia.org/wiki/File:Snowy_egret_in_profile.jpg), Serebit | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Forest canopy | [Forest covered hills on Yakushima](https://commons.wikimedia.org/wiki/File:Forest_covered_hills_on_Yakushima.jpg), Grendelkhan | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Gray fur | [Racoon clinging to a tree](https://commons.wikimedia.org/wiki/File:Racoon_clinging_to_a_tree.JPG), Korall | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) |
