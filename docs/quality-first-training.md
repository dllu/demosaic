# Quality first: V43 architecture, cleaner data and retained fine detail

The priority is a convincing quality improvement over V43 step 2000. Speed work
is deferred. Keep V43's original full-resolution pretrained RGB network,
physical noise anchors/conditioning and genuine frozen DINOv3 ViT-S/16
architecture. Later ConvNeXt, RAW-native and refinement experiments do not become
the starting architecture for this study.

## Corpus review

The available reviewed Commons corpus contains 88,508 training images at 4×/8×,
versus V43's original 40,170. Original validation 2,303 / test 2,255 memberships
stay fixed. Actual downloading stopped at the reserve with 178,117 originals;
archive discovery/attribution are complete and 279,548 originals remain pending.

The [illustrated source review](corpus-source-review.md) currently covers 322
sources: 299 retain and 23 withhold, including all 74 training sources with
recorded ISO ≥12800. Native examples show why processed targets are withheld
while real fine leaf veins and weak fog detail remain. High loss, ISO and
software tags select review candidates; visible binned-target quality decides
membership. This is targeted review, not a full-corpus manual inspection.

The full V43 loss/IQA-proxy scan is still running. Final curation requires its
completed receipt, visual decisions for the top 32 under each noise condition
and top 16 under each proxy, plus all additional reviewed-source decisions.
Apply exclusions through new manifests while preserving protected series,
the GFX scene/siblings and historical data. Ranking/supervision details,
header-inventory evidence and the membership-freeze command are in the
[source-review guide](corpus-source-review.md).

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
