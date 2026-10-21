# Completion evidence

The objective remains the full [PROMPT](../PROMPT.md), including trained image
quality. **It is not complete.** V43 step 2000 remains the working experimental
reference. Current work returns to its architecture, a larger visually curated
Commons corpus and less blur/more low-contrast detail in training. Quality takes
priority; speed experiments are deferred.

## Requirements and current evidence

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| State-of-the-art joint demosaicing and denoising | Trained comparisons with strong baselines, fixed held-out protocols and convincing native detail | **Unproven.** Later models improve some aggregate scores but retain detail/color/camera tradeoffs. See the [experiment index](experiments.md) and [PSNR history](performance-history.md); version number alone does not rank quality. |
| Decisively better real-photo quality than RawNIND | Broad matched native comparisons across cameras, scenes, shadows, textures and clipping boundaries | **Unproven.** [Cross-camera comparisons](cross-camera-qualitative.md), [GFX detail](mature-cudnn-fullframe.md) and [colored-light contexts](gfx-highlight-qualitative.md) provide examples, but do not establish the requested broad superiority. |
| 16-bit support and practical full-resolution output | Actual RAW processing, numerical checks and uint16 RGB TIFF exports | Demonstrated on the 101.996 MP GFX capture, including complete float-array/export checks and [actual CLI validation](mature-cudnn-fullframe.md). This does not establish sufficient restoration quality. |
| 100 MP within 10 seconds on GB10 | Actual whole-photo measurement on a quality-qualified model, with clear timing scope | **Unmet.** The mature V43 FP32 report records 118.22 s warmed and a separate 166.67 s restore including search. These scopes differ. Resident tile ratios and faster rejected models do not prove this requirement. New speed work is deferred. |
| Modern method with DINOv3 | Pinned licensed backbone, architecture rationale and measured ablations | Implemented with approved DINOv3 weights and recorded licenses; [research](research.md) and architecture experiments remain available. The new quality study preserves V43's frozen ViT-S/16 bottleneck architecture. Implementation alone is not SOTA evidence. |
| Free, diverse training data and aggressive binning | Attribution, fixed holdouts, actual corpus training and reproducible augmentation | The completed scan covers 88,508 training sources; actual targeted visual review of 371 withholds 24. Frozen matched cohorts contain 39,983 control / 88,484 larger training sources, with unchanged 2,303 val / 2,255 test memberships. The [curation receipt](results/v43-quality-curation-and-training-plan-v1.json), [data extension](commons-post4557-reviewed.md) and [4× → geometry → area2 pipeline](training-pipeline.md) retain the evidence. New matched V43 stages are **in progress**: all six preflights pass, V93/V94 completed20k, and V95 is running after explicit resource recovery; new model quality is unmeasured. |
| Appropriate noise/exposure and camera handling | Physical observations, signed/negative-noise handling, highlight/shadow tests and real-camera checks | Implemented and tested, with remaining quality limitations documented in [evaluation](evaluation.md). Camera references and assumed noise priors retain their stated limits. |
| Training and shared-machine operation | Locked Python/PyTorch/uv environment, bounded jobs, restart/data checks and real GB10 execution | Implemented. The [current quality plan](quality-first-training.md) records focused tests, actual CPU/CUDA preflights, paired input checks, resource bounds, completed controls and explicit V95 recovery with archived failure evidence. |
| Read-only originals and protected real-photo evaluation | Audited training manifests, local GFX cache and preserved source bytes | Standing policy: originals stay read-only; GFX DSCF3879/3880 and siblings stay outside training. The locally cached scene includes sky, buildings, foliage and fence. The ISO100 image is a separate qualitative reference, not exact GT. |
| Reproducible reports and current documentation | Native crops, source/ROI/weights/noise/display metadata, diary, setup commands and Git history | Current [README](../README.md), [documentation guide](index.md) and per-study reports retain the evidence. Diary filenames now use DST-aware Los Angeles time; [the correction map](../diary/timestamp-corrections.json) preserves historical body hashes. Meaningful progress is committed and pushed. |

## Current quality work

The [V43 quality study](quality-first-training.md) separates the larger-corpus
effect from the blur/low-contrast augmentation package using matched controls.
The completed source screen covers training rows only. High loss and image-quality
proxies selected candidates for actual visual review; they never automatically
labeled a photograph bad. Independent checks confirm the final curated cohorts
preserve holdouts, selected row contents and inherited protected-series
exclusions. All six [fresh CPU/CUDA checks](results/v43-quality-final-curated-preflights-v1.json)
pass, both [V93](results/v43-quality-V93-completed-training-v1.json) and
[V94](results/v43-quality-V94-completed-training-v1.json) completed20k, and V95 is
running with resource telemetry after resource-guard interruptions. New model quality remains
unmeasured until production and full review finish.

Completed later studies, including [V92](late-rgb-head-only-original4k-review.md),
retain their unfavorable evidence. Higher PSNR in one panel, finite training,
successful CPU/CUDA execution, or more data alone does not establish a quality
improvement or justify promotion.

## Evidence required before completion

- Evaluate trained endpoints against V43 and strong comparators on the fixed
  photographic and measured-CFA panels; retain per-source/condition results and
  uncertainty rather than relying on one average.
- Inspect weak low-contrast detail, ADC-only reconstruction, noise, color,
  highlights and real-camera scenes. Each improved-model report needs at least
  two small native noisy/denoised/exact-GT crop triplets with matching coordinates
  and transforms, no pixel resizing, checkpoint hash, noise and display exposure.
  Independently demosaiced or different-exposure real references are labeled
  accurately. Keep representative crops in the README.
- Establish the requested restoration quality and broad real-photo advantage;
  then qualify that model on an actual 100 MP 16-bit run. Report timing scope and
  whether the 10-second target is met. Quality remains the higher priority.
- Preserve reproducible inputs, manifests, licenses, source/checkpoint hashes,
  validation artifacts, local-time diary entries and successful Git pushes.

The [historical completion-evidence log](requirements-archive.md) preserves the
previous chronological record unchanged after its archive header. Its old
"pending" statements describe their original dates; they are not current job
status. Detailed experiment evidence remains linked from the experiment index.
