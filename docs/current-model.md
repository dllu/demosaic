# Current models and development baseline

**V102 final20k has the best selected natural-detail results; V101 final10k
remains the default with complete full-panel results.** Both continue V84's
full-resolution pretrained DRUNet RGB trunk,
physical noise anchors and frozen official DINOv3 ConvNeXt-Tiny pyramid.
V84 remains the architectural reference; V43 is a historical comparator.

| Version | Photo sRGB PSNR | Known-camera CFA PSNR | Unseen-camera CFA PSNR | Main use |
| --- | ---: | ---: | ---: | --- |
| V43 | 34.89934 | 54.23332 | 53.80606 | Earlier ViT-S baseline |
| V84 | 36.43996 | 54.17122 | 53.92823 | Strong architectural reference |
| V85 | 36.43574 | 54.17942 | 53.93069 | Similar quality, expanded native targets |
| V95 | 35.29553 | **54.33307** | 53.76990 | Stronger tested weak-carrier response |
| V99 | 35.40133 | 54.31940 | 53.72165 | ADC-consistency experiment |
| V100 | 36.47264 | 54.17846 | 53.89614 | Curated-cohort continuation; camera tradeoff |
| **V101** | **36.50347** | 54.17404 | 53.92334 | **Preferred quality/training checkpoint** |

V101 improves photo PSNR by +.06351 dB over V84, with 418/427 source means
improving and gains in all seven conditions. SSIM, chroma and gradient error
also improve on the photographic mean. Its known/unseen CFA changes versus
V84 are +.00282/−.00488 dB; both small-scene intervals include zero. These gains
and tradeoffs support using V101 while continuing to improve real fine detail.
[Completed matched results, intervals and native crops](v84-curated-quality-review.md).

**V102's original20k endpoint** gains +.362/+.285/+.043dB over V101 on the
four-source ADC/ISO100/ISO12800 detail panel. PSNR, SSIM, chroma and gradient
error improve in all12 cases versus both V101 and fixed V102@5000. Its
[native detail gallery](heldout-detail.md) and
[six-region GFX comparison](gfx-qualitative.md#v102-at-5000-and-20000-updates)
are current. Real GFX remains close and fine detail is still soft. The latest
checkpoint is available now at `/mnt/external/demosaic/models/v102-final20000.pt`.
Use it for continued detail development; V101 supplies the completed
full427/camera/full-frame measurements. V103 is running, with the full matched
evaluation queued. The selected12 cases are not added to the full-panel table.

V84 gains about **1.54 dB over V43** on the full fixed photographic panel and
has a higher unseen-camera mean. Its known-camera mean is slightly lower.
The stronger ConvNeXt family is a useful advance despite that small-panel
tradeoff. V84/V85 also reduce bright-magenta mottling relative to their V63
parent. V95 retains more of a tested noisy low-contrast carrier, but introduces
larger color errors in some natural images. These differences guide development;
there is no requirement that one version win every diagnostic before we use it
or publish its progress.

Photo means cover 427 images, seven conditions and four CFAs. Camera means
cover four/five development scenes and use measured CFA targets. Versions have
different training budgets and data; this table compares available checkpoints,
not an isolated architectural ablation. [Full history and provenance](performance-history.md).

V84/V100/V101 now have a complete matched CUDA IEEE FP32 photographic and
known/unseen-camera comparison. The [camera guide](real-camera-quality.md)
shows per-scene changes and accurately labeled AHD reference crops; it also
preserves the earlier V84/V100 CPU report. V101 recovers most of V100's
unseen-camera loss, while auxiliary RGB detail/color differences remain.

V84's gain over V43 is larger in the low-noise conditions than the existing
ISO 12800 gallery suggested:

| Photographic condition | V84−V43 sRGB PSNR, dB |
| --- | ---: |
| ADC-only | +2.30 |
| ISO 100 prior | +2.01 |
| ISO 1600 prior | +1.40 |
| ISO 12800 prior | +0.57 |
| Shadows | +0.33 |
| Highlights | +3.21 |
| Legacy noise | +0.96 |

These descriptive means cover all 427 photos and four CFAs per condition.
Each photo's average over all 28 condition/CFA combinations improves; 24 of
11,956 individual cases regress. The paired source interval for the overall
+1.54 dB change is [+1.46,+1.62] dB. This describes source variation, with unequal model training
histories. [Per-condition counts, scores and provenance](results/v84-v43-photographic-comparison-v1.json).

## Native comparisons

The newest [full-panel native comparison](v84-curated-quality-review.md#native-photographic-comparisons)
contains two shared noisy/restored/GT triplets per V84/V100/V101 checkpoint.
The [natural-detail gallery](heldout-detail.md) and README highlight V102's final20k
low-noise progress. The older comparisons below retain the larger V84−V43
advance and explain the architectural choice.

Each cell below is an unchanged 160×160-pixel crop. The same source coordinates,
conditioning and display transforms apply across methods. Synthetic references
are exact for the simulated observations. All images and complete per-method
source/checkpoint/ROI metadata accompany each gallery; the
[high-noise/GFX manifest](images/current-quality/manifest.json) covers the earlier crops.

The same two fixed photographic examples at ISO 100 show a clear V84 improvement
in fine suspension lines, broad orange color and building boundaries. RawNIND
uses input-only CFA-channel gain. These fresh CPU observations share source,
noise, display and exact GT pixels across methods; the full-panel scores above
retain their original CUDA evaluations.

![ISO100: noisy, V43, V84, RawNIND and exact synthetic GT](images/current-quality/iso100-prior/photo-comparison.png)

[ISO100 source/ROI/checkpoint metadata](images/current-quality/iso100-prior/manifest.json) ·
[ADC-only comparison](images/current-quality/adc-only/photo-comparison.png)
([metadata](images/current-quality/adc-only/manifest.json)).
V84's ISO100 triplets: [fabric](images/current-quality/iso100-prior/V84-0014aa4e075b.png)
([metadata](images/current-quality/iso100-prior/V84-0014aa4e075b.json)) and
[building](images/current-quality/iso100-prior/V84-002fc6eeadf6.png)
([metadata](images/current-quality/iso100-prior/V84-002fc6eeadf6.json)).

At ISO 12800, the models remain much closer and suppress fine cords:

![Noisy, V43, V84, V95, V99 and exact synthetic GT on fabric and building crops](images/current-quality/photo-comparison.png)

V84's high-noise triplets: [fabric](images/current-quality/photo-V84-0014aa4e075b.png)
([metadata](images/current-quality/photo-V84-0014aa4e075b.json)) and
[building](images/current-quality/photo-V84-002fc6eeadf6.png)
([metadata](images/current-quality/photo-V84-002fc6eeadf6.json)).

V84 retains the fabric's broad orange color more faithfully than V95/V99 in
this high-noise example. Fine cords remain a development target for every model.
The [GFX page](gfx-qualitative.md) compares sky, building, foliage and fence at
native sensor resolution, now adding both completed V100/V101 continuations
and two illuminated regions. The learned checkpoints look close there; RawNIND
and the separately captured ISO100 reference remain explicit comparators.
The [natural-detail gallery](heldout-detail.md) adds bark, white feathers,
forest canopy and fur at three noise levels. It shows V84's remaining
high-noise detail loss as well as its sharper low-noise output.
V101's completed reduced-blur/detail continuation gains PSNR/SSIM on all12
selected cases against V84 and the V100 control. The current gallery adds
V102@20000 alongside fixed5000, with further low-noise gains and remaining high-noise smoothing. The
completed full-panel comparison confirms a smaller but widespread photographic gain.
For explicitly ADC-only inputs, use the [optional site correction](adc-consistency.md):
it gains .400dB rendered PSNR over unchanged V84 weights across all427 photos,
with all1,708 CFA cases improving. The complete report shows native examples
and color/detail tradeoffs. Positive-noise profiles bypass it; the seven-condition
values above and the original V84 training initializer remain unchanged.
The [complete real-camera comparison](real-camera-quality.md) records the small
CFA changes and remaining auxiliary RGB tradeoffs.
The [Q2, Sony a7R II and GFX50R gallery](cross-camera-qualitative.md) also
compares V84/V100 with V43 and RawNIND on six fixed native ROIs. Those
low-ISO captures show closer results, with the clearest RawNIND separation
on concrete texture; there is no clean reference.

The [completed V84/V85 study](native-data-original20k-review.md) retains detailed
metrics, uncertainty, color/weak-detail diagnostics and capture limitations.
Its [bright-magenta comparison](images/native-data-hue-all-methods-native.png)
shows the reduction in V63's spatial color mottling in V84/V85.
Its stringent original study gates answered whether adding 22 native captures
demonstrated a particular matched benefit. They do not erase V84's absolute
improvement or determine the current baseline. Immutable receipts and diary
entries retain the original decisions.

## Use the current checkpoint

Local checkpoint: `/mnt/external/demosaic/models/v101-final10000.pt`.
SHA256: `6f691c653a618bdde0d7db501f3efc557a9699e2dbba73cf94c7440b364ef3e3`.
The canonical copy matches the completed training artifact byte-for-byte.
[Current selector and completed-owner verification](results/current-model-V101-selection-v1.json).
Inference selects its final EMA; the official DINOv3 checkpoint loads separately
from the local Hugging Face cache. See [usage](usage.md).

V100/V101 continue V84 for 10,000 updates with fresh AdamW/EMA on the cleaned
88,484-source cohort. V101 removes optical PSFs and adds weak textures,
photographic contrast attenuation and six reviewed detail ROIs. Their matched
comparison tests the complete recipe, without isolating individual components.
The [88,477-source cohort and 32-region catalogue](corpus-source-review.md)
are now used by the matched V102/V103 continuation. V102's original20k selected
detail/GFX results are published; V103 and full matched evaluation continue.
Keep current guides and comparisons updated as useful versions
appear; the timestamped diary retains chronological decisions.
