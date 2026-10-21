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

The [illustrated source review](corpus-source-review.md) covers 371
sources: 347 retain and 24 withhold, including all 74 training sources with
recorded ISO ≥12800. Native examples show why processed targets are withheld
while real fine leaf veins and weak fog detail remain. High loss, ISO and
software tags select review candidates; visible binned-target quality decides
membership. This is targeted review, not a full-corpus manual inspection.

The full V43 loss/IQA-proxy scan completed all 88,508 training sources and
177,016 cases. All 87 distinct final top-32/top-16 candidates have visual
decisions. New manifests apply the 24 exclusions while preserving protected
series, the GFX scene/siblings and historical data. The independently checked
cohorts contain **39,983 control / 88,484 larger training sources**, with unchanged
2,303 validation / 2,255 test memberships. Ranking/supervision details,
header-inventory evidence and the membership-freeze command are in the
[source-review guide](corpus-source-review.md).

## Matched V43 training comparison

The frozen study uses the curated larger corpus and its intersection with the
original V43 cohort. Existing protected/series and new bad-source exclusions
apply to both. Validation and native128/paired32 data stay fixed.
Every arm starts from the same original V43 step 2000 EMA, with a
fresh optimizer/EMA and common seed/schedule. These are new training stages.

| Arm | Commons sources | Optical PSF probability | Low-contrast examples |
| --- | --- | ---: | --- |
| V93 small-cohort control | 39,983: original cohort intersected with eligible/curated IDs |.25|Original mix|
| V94 larger-data control | 88,484: full curated larger corpus |.25|Original mix|
| V95 fine-detail recipe | Same 88,484 sources as V94 |0|More weak procedural detail and contrast-attenuated photos|

V94−V93 measures larger curated membership; V95−V94 measures the augmentation
package. Architecture stays fixed. Keep batch 16 and 25% paired/25% native/50%
Commons. Plan equal 20,000-update stages with diagnostic intermediate checkpoints.
Learning-rate/initializer/source settings and resource bounds are frozen in the
[production plan receipt](results/v43-quality-curation-and-training-plan-v1.json).

New opt-in controls are `optical_blur_probability` (default 0.25),
`raw_clean_optical_blur_probability` (inherits it), and
`photographic_low_contrast_fraction` (default 0). V95 uses 0 optical blur,
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

All six [final-cohort CPU/CUDA preflights](results/v43-quality-final-curated-preflights-v1.json)
passed: 24 discarded updates per arm/phase, 144 actual training/DINO forwards.
Independent checkpoint/metric checks pass, and paired/native observations match
across controls as required. **V93 and V94 completed 20,000 updates each; V95 is
running its fine-detail treatment.** Independent saved-state audits of
[V93](results/v43-quality-V93-completed-training-v1.json) and
[V94](results/v43-quality-V94-completed-training-v1.json) verify final EMAs,
retained checkpoints, optimizer counters and input traces. Full matched quality
evaluation and native crop review remain pending.

The launcher can reserve a fresh `/mnt/external/demosaic` artifact directory
through `--artifact-root`. Plans/code remain local; checkpoints and run traces
use the external SSD. This prospective training policy keeps 64 GiB free on the
system disk and 384 GiB externally. Its path/ownership preparation check passes
without allocating checkpoints or launching a controller. The current source
scan completed under its original 500 GiB external floor. The production plan
is frozen at `.cache/quality-first-20261020/V43-curated-matched-training-v1/`.
Its controller requires 48 GiB available RAM sustained for 60 s before each
stage, with a two-hour resource-wait bound. Initial headroom was about 11 GiB;
the original controller waited, then ran the six preflights and completed both
controls. V95 stopped around logged step1,025 when the system-disk reserve was
crossed. Its unsaved partial trial is archived. After
[relocating cold checkpoint copies](results/cold-checkpoint-relocation-20261021-v1.json)
to restore about 32 GiB, explicit manual recovery restarts only V95 from the same
original V43 weights/configuration. The
[recovery receipt](results/v43-quality-V95-manual-recovery-v1.json) records exact
replay of all 42 logged input batches through step1,025. The completed controls and passed preflights
are reused. All resource bounds stay fixed, including the 24 GiB active RAM floor.
Check the original `status.json` for live progress; it records the recovery plan.

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
