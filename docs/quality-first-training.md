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

The original worker remains running under an explicit supervision handoff at
`.cache/quality-first-20261020/corpus-source-screen-supervision-v2/status.json`.
Its projected duration was close to the first controller's six-hour bound;
the new ceiling is eight hours from the **original** worker start. The scoring
plan/source, PID, checkpoint, inputs and 24 GiB RAM / 64 GiB root / 500 GiB
external reserves are unchanged. The exact old supervisor exited; the worker
was neither stopped nor restarted. Use the new status path, since the old
controller's preserved status is historical.

Rank high-loss images alongside low-gradient, high-frequency and bright/clipped
proxies. Inspect full-source context and native pixels for grain, blur,
oversharpening, processing artifacts and non-photographic content. **High loss
alone is not an exclusion rule**: fine foliage, textiles, fences and other useful
hard detail should remain. Record visual decisions by source ID and reason.
Use a new training manifest; preserve originals, historical manifests, protected
series and the GFX scene/siblings. This is targeted review, not a claim that
every corpus photo was manually viewed.

The [current 163-source visual review](results/source-quality-visual-review-v5.json)
withholds ten sources: a historic map scan, a photomontage, five graphic-only
compositions, a predominantly
defocused station scene, and two images with visible noise/edge artifacts
whose clean-target quality is uncertain. The other 153 remain, including fine
foliage, wheat, fur, coral, architectural grids and hazy/low-contrast landscapes.
Thirty contact sheets and six larger native 1024 crops were actually inspected.
The full ranking is still running; this is an initial review, not the final
curated manifest or a trained-model result.

The expanded title-cue review withholds graphic-only letter/illustration and
textured tessellation compositions. The [Escher creator description](https://commons.wikimedia.org/wiki/File:Ambigram_tessellation_Escher.jpg)
corroborates its pattern-design intent; no particular pixel-generation pipeline
is inferred. Physical stamps, tattoos, carvings and the
[pencil/paper study](https://commons.wikimedia.org/wiki/File:Ambigram_Nothing_written.jpg)
remain eligible based on their visible material detail and context. All nine
inspected processing-title candidates remain, including a camcorder whose model
name contains HDR. Software/HDR/title tags alone never decide exclusion.

The final membership freeze requires visual decisions for the top 32 sources
under each noise condition and the top 16 under each IQA proxy, plus all
additional sources already reviewed. `scripts/freeze_v43_curated_corpus.py
--help` describes the freeze; `--check` lists pending decisions without writing
training manifests. It checks the completed ranking receipt, source identities,
the exact original V43 cohort and unchanged holdout memberships. Exclusions
affect future training membership only.

An additional posthoc ADC-error/local-gradient ratio review retained all twelve
new selected sources: it mostly found legitimate smooth skies, saturated
gradients and bright boundaries. Small denominators and model error affect this
cue; it does not identify bad photographs reliably by itself. This reused partial
source scores, with no additional inference or automatic exclusions.

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

A [discarded CPU training proof](results/v43-quality-CPU-training-proof-v1.json)
also completes 24 actual V43 updates from its exact original EMA and architecture,
covering Commons, native RAW and paired RAW. It executes three photographic
contrast attenuations and one weak-texture sample, with zero optical PSFs;
DINO stays frozen and gradients, optimizer state and EMA remain finite.
This uses batch 1/native 32 before curation and provides no model-quality,
production CUDA, throughput or validation result. The focused data/training
checks pass 53 tests with one skip.

The [matched launcher CPU proof](results/v43-quality-launcher-CPU-proof-v2.json)
then verifies all three arms on explicitly provisional memberships: 24 discarded
updates per arm, 72 in total. All start with the exact original V43 EMA and fresh
optimizers; the 71 model/71 EMA tensors and 69 Adam states are finite. All owners
exit successfully. The data-only comparison preserves all 15 shared paired/native
observations and changes five Commons observations; the fine-detail comparison
preserves all ten paired observations and changes six treatment observations.
Final Python/CPU/CUDA RNG states match across arms. Source archives differ only
in the training manifest for the membership comparison and are identical for
the augmentation comparison. This remains CPU/B1/native32 engineering, with no
quality or timing claim.

`scripts/train_v43_quality_trial.py` prepares the production freeze only from a
completed final curation receipt. It checks that membership and augmentation
are the only recipe differences, and that native/paired/validation manifests
match the original V43 lineage. The launcher runs fresh CPU checks and discarded
CUDA/B16/native256 checks before any of the three 20k stages. It enforces memory,
disk and runtime bounds, keeps caches in authorized storage, retains 4k/8k/12k/16k
diagnostic checkpoints, and uses the fixed 20k final EMA as the primary endpoint.
The training-validation best checkpoint is separate. Failures are preserved;
there is no automatic retry or promotion. **The production plan is not yet
frozen or launched**, because full source ranking and final review are pending.

The [CPU reporting integration](results/v43-quality-reporting-CPU-proof-v4.json)
also passes using the original V43 and three actual discarded 24-update EMAs:
48 genuine neural/DINO forwards, 84 metric rows, and eight native 160-pixel
triplets from two held-out photographs. All 24 panels were actually viewed.
The noisy/GT pixels match exactly across methods, as do the display settings;
independent summary arithmetic has zero discrepancy. Weights, configuration,
parameter identities, RNG and declared inputs stay unchanged. This small
CPU/native176/B1, two-condition/two-CFA check supplies no quality gain, production
CUDA or full-panel qualification. Earlier probe output-path/metadata-format
failures and their outputs are preserved in the receipt. Full evaluation still
uses all 427 photos, seven conditions, four CFAs and native256.

## Quality review

Compare completed endpoints with V43 and matched controls on the fixed 427-photo
panel, known/unseen measured-CFA panels, low-contrast ADC/noisy carriers,
flat/color fields and GFX sky/building/foliage/fence/highlight contexts. Retain
per-condition/source results and uncertainty. Inspect native crops before
aggregate interpretation. Each model report includes at least two native
noisy/restored/exact-GT triplets and accurately labeled real references, with
checkpoint/ROI/noise/exposure metadata. No faster inference or new full-frame
benchmark is part of this work.
