# Quality first: V43 architecture, cleaner data and retained fine detail

The priority is a convincing quality improvement over V43 step 2000. Speed work
is deferred. Keep V43's original full-resolution pretrained RGB network,
physical noise anchors/conditioning and genuine frozen DINOv3 ViT-S/16
architecture. Later ConvNeXt, RAW-native and refinement experiments do not become
the starting architecture for this study.

## Corpus review

The available reviewed Commons corpus contains 88,508 training images at 4×/8×,
versus V43's original 40,170. Original validation 2,303 / test 2,255 memberships stay
fixed. Archive discovery/attribution are complete; actual downloading stopped
at the reserve with 178,117 originals and 279,548 still pending.

A source-frozen scan under
`.cache/quality-first-20261020/corpus-source-screen-v1/` uses the actual V43
step2000 checkpoint, IEEE FP32 and fixed ADC-only/ISO12800 conditions. It scores
a native 256 center crop from the 4× cache plus final area2, without geometric
or optical augmentation. Only training rows enter. A genuine four-source/native 64
CPU proof passes before GPU scoring; a separate unit check matches every
per-image loss term to V43's original training objective.

Rank high-loss images alongside low-gradient, high-frequency and bright/clipped
proxies. Inspect full-source context and native pixels for grain, blur,
oversharpening, processing artifacts and non-photographic content. **High loss
alone is not an exclusion rule**: fine foliage, textiles, fences and other useful
hard detail should remain. Record visual decisions by source ID and reason.
Use a new training manifest; preserve originals, historical manifests, protected
series and the GFX scene/siblings. This is targeted review, not a claim that
every corpus photo was manually viewed.

The [first 31-source visual review](results/source-quality-first31-visual-review.json)
withholds four sources: a historic map scan, a photomontage, a predominantly
defocused station scene, and an event image with visible noise/edge artifacts
whose clean-target quality is uncertain. The other 27 remain, including fine
foliage, fur, coral, architectural grids and hazy/low-contrast landscapes.
Seven contact sheets and four larger native 1024 crops were actually inspected.
The full ranking is still running; this is an initial review, not the final
curated manifest or a trained-model result.

## Matched V43 training comparison

After review, freeze the curated larger corpus and its intersection with the
original V43 cohort. Apply existing protected/series exclusions and newly
identified bad-source exclusions to both. Keep validation and native128/paired32
data fixed. Every arm starts from the same original V43 step 2000 EMA, with a
fresh optimizer/EMA and common seed/schedule. These are new training stages.

| Arm | Commons sources | Optical PSF probability | Low-contrast examples |
| --- | --- | ---: | --- |
| V93 small-cohort control | Original cohort intersected with current eligible/curated IDs |.25|Original mix|
| V94 larger-data control | Full curated larger corpus |.25|Original mix|
| V95 fine-detail recipe | Same curated larger corpus as V94 |0|More weak procedural detail and contrast-attenuated photos|

V94−V93 measures larger curated membership; V95−V94 measures the augmentation
package. Architecture stays fixed. Keep batch 16 and 25% paired/25% native/50%
Commons. Plan equal 20,000-update stages with diagnostic intermediate checkpoints.
Exact learning-rate/initializer/source settings and resource bounds will be
frozen with the actual reviewed manifests before launch.

New opt-in controls are `optical_blur_probability` (default 0.25),
`raw_clean_optical_blur_probability` (inherits it), and
`photographic_low_contrast_fraction` (default 0). V95 proposes 0 optical blur,
`.15` weak textures within the existing `.2` procedural fraction, and `.25`
low-contrast probability conditional on a photographic Commons sample. Natural
detail is continuously attenuated by 0.125–.5 around channel means, preserving
pixel geometry and mean color. Paired RAW stays unchanged. Geometry remains
between 4× binning and final 2× reduction.

Tests preserve old augmentation pixels/RNG exactly, show zero probability
executes no optical kernel, and check continuous low-contrast geometry/means.
Resume rejects changed probabilities/fractions. These are data-path checks,
not evidence of a trained quality gain.

## Quality review

Compare completed endpoints with V43 and matched controls on the fixed 427-photo
panel, known/unseen measured-CFA panels, low-contrast ADC/noisy carriers,
flat/color fields and GFX sky/building/foliage/fence/highlight contexts. Retain
per-condition/source results and uncertainty. Inspect native crops before
aggregate interpretation. Each model report includes at least two native
noisy/restored/exact-GT triplets and accurately labeled real references, with
checkpoint/ROI/noise/exposure metadata. No faster inference or new full-frame
benchmark is part of this work.
