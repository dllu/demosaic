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

The [current 269-source visual review](results/source-quality-visual-review-v11.json)
withholds twenty sources: a historic map scan, a photomontage, eight graphic-only
or flat document compositions, a predominantly
defocused station scene, and nine images with visibly unreliable clean-target
texture/noise/edge quality. The other 249 remain, including fine
foliage, wheat, fur, coral, architectural grids and hazy/low-contrast landscapes.
Fifty contact sheets and twenty larger native 1024 crops were actually inspected.
The full ranking is still running; this is an initial review, not the final
curated manifest or a trained-model result.

One withheld foliage source has extensively flattened/patchy texture and stepped
color regions in a larger native view; those defects remain in the binned target.
This is a visual target-quality decision, without inferring a particular filter.
The context thumbnail is resized; the two 256-pixel crops retain their native
pixels. Source ROI `[1736,1340,256,256]`; bin4 target context
`[210,111,512,512]` followed by area2; display exposure ×1.0. The
[figure metadata](results/source-quality-flattened-foliage-example.json) records
source hashes, transforms, the V43 screening checkpoint and both noise conditions.

![Withheld foliage source: context thumbnail, native source crop and native 8x-binned target](images/source-quality-flattened-foliage.png)

Source: [Diego Delso, Brown County State Park](https://commons.wikimedia.org/wiki/File:Vista_desde_la_torre_de_observaci%C3%B3n,_Parque_Estatal_Brown_County,_Indiana,_Estados_Unidos,_2012-10-14,_DD_08.jpg),
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Modified through
binning, cropping, display conversion and context-thumbnail creation.

The expanded title-cue review withholds graphic-only letter/illustration and
textured tessellation compositions. The [Escher creator description](https://commons.wikimedia.org/wiki/File:Ambigram_tessellation_Escher.jpg)
corroborates its pattern-design intent; no particular pixel-generation pipeline
is inferred. Physical stamps, tattoos, carvings and the
[pencil/paper study](https://commons.wikimedia.org/wiki/File:Ambigram_Nothing_written.jpg)
remain eligible based on their visible material detail and context. All nine
inspected processing-title candidates remain, including a camcorder whose model
name contains HDR. Software/HDR/title tags alone never decide exclusion.

A [complete header inventory](results/source-capture-metadata-review-v1.json)
finds positive recorded ISO in 82,094 training sources, including 1,370 at ISO
3200 or above. It reads JPEG/MPO headers without pixel decoding or inference.
Eight highest-ISO sources plus eight deterministic high-ISO samples were
actually viewed. Four bird photos have heavily etched/flattened feather texture
and enhanced outlines that persist in the binned targets; withhold those.
Twelve remain, including other high-ISO wildlife, water drops, portraits,
architecture and fine lettering. ISO and software tags remain review cues only.
EXIF warnings are preserved; metadata does not prove capture provenance or
clean-target quality. This targeted sample is not a corpus defect-rate estimate.

A posthoc followup inspects the next 24 highest recorded-ISO sources not already
reviewed, using four more sheets and seven larger native crops. Two have strong
outlined/flattened feather texture that remains visibly altered after binning;
withhold them. The other 22 remain, including wildlife, action portraits, water
drops, architecture and HDR-labeled interiors. Across both ISO-targeted rounds,
40 sources were actually viewed and six withheld. These are selected extremes,
not a random sample. Native grain or edge emphasis alone is insufficient when
the binned target retains useful coherent detail.

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

Data-path tests preserve legacy augmentation pixels/RNG and cover zero-PSF and
low-contrast behavior. Genuine discarded CPU training, matched-arm, reporting
and validation-boundary checks pass; see the [validation evidence](quality-training-validation.md).
These engineering checks do not establish a quality gain. The launcher requires
final reviewed manifests, then fresh CPU and CUDA/B16/native256 checks before
three matched 20k stages. Final-step EMA is the primary endpoint, with training
validation best and 4k/8k/12k/16k diagnostics retained separately.

The launcher can reserve a fresh `/mnt/external/demosaic` artifact directory
through `--artifact-root`. Plans/code remain local; checkpoints and run traces
use the external SSD. This prospective training policy keeps 64 GiB free on the
system disk and 384 GiB externally. Its path/ownership preparation check passes
without allocating checkpoints or launching a controller. The current source
scan retains its original 500 GiB external floor. **Production is not yet
frozen or launched**; complete ranking and final review come first.

## Quality review

Compare completed endpoints with V43 and matched controls on the fixed 427-photo
panel, known/unseen measured-CFA panels, low-contrast ADC/noisy carriers,
flat/color fields and GFX sky/building/foliage/fence/highlight contexts. Retain
per-condition/source results and uncertainty. Inspect native crops before
aggregate interpretation. Each model report includes at least two native
noisy/restored/exact-GT triplets and accurately labeled real references, with
checkpoint/ROI/noise/exposure metadata. No faster inference or new full-frame
benchmark is part of this work.

`scripts/evaluate_v43_quality_trial.py` prepares evaluation only after the matched
training controller and workers finish. It pins the four checkpoint bytes,
training-source snapshot, observations and protocol, then runs photo, known,
unseen, weak-detail, color and two GFX stages serially. Fresh IEEE FP32 is shared
across all endpoints; historical means retain their original compute metadata.
RawNIND's global/per-channel input-only adapters appear in photo/real/GFX panels.
Each stage checks frozen DINO/state, predictor arguments and native crop pixels;
the primary photo/real summaries also receive independent coverage/arithmetic
checks. Outputs still require actual native viewing and interpretation.
The [CPU launcher integration](results/v43-quality-evaluation-launcher-CPU-proof-v3.json)
passes on discarded checkpoints; it does not qualify the production branches.
