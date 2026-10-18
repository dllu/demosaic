# Complete 40k quality/native review and reject compiled accuracy

Previous goal turn made progress in5052e28: independently reduced the finished
camera panels and inspected six native progress assets. This turn completes
the full frozen40k workflow and manual selected-native review. Exact owners
and final children of training, quality review and compilation have exited;
no job was restarted or source/protocol changed.

Full427 photo means are29.732067/.883240 without DINO and29.953265/.886787
with DINO. Own8k gains are+2.061197dB [2.016179,2.106169] and+2.188114dB
[2.135696,2.234338]. The DINO photo gap is+.221198dB [.198978,.244619],
remaining about+.221dB on both fixed418/416-source sensitivity cohorts.
These source bootstraps do not establish complete scene independence,
training-repeat uncertainty or absence of prior pretraining exposure.
Known/unseen CFA scores48.2818/46.1458 and48.3667/46.0103 still trail Wiener
and mature controls. Photo scores remain5–6dB below V43/V63. Neither endpoint
is promoted or extended; V43 stays the working reference.

The completed numerical workflow has648/810 camera cases,111,636 full
photographic/procedural cases,2,240 analytic cases,128 selected color arrays,
4,704 hue cases (2,352 fresh plus2,352 verified reuse),132 comparisons,
33 classical witnesses and99 source sensitivities. All planned artifact,
selected-color, hue-group, supplemental-highlight and sensitivity audits pass.
Integrity checks include76 PNGs,32 F32 arrays,eight NN RGB16 files and four
additional RawNIND RGB16 files, with declared native display-rounding checks.
Integrity is kept distinct from actual visual review.

Prepared/inspected all126 selected source triplets in unchanged160px panels:
24 camera,12 photographic,24 GFX,54 camera/color/hue/highlight and12 analytic.
The saved operator/receipts/manual notes are at
`/mnt/external/demosaic/benchmarks/packed-isotropic-quarter-native-inspection-v1/`.
Photo/GFX progress grids include identical8k/40k/control/noisy/reference pixels;
photo cache coordinates are independently recovered from the declared dataset
RNG. No model forward, GPU work or resampling was added for inspection.
The synthetic GT is exact only for its observation; registered/AHD/ISO100
references and same-capture RawNIND comparators are accurately labeled.

The new models reduce grain but leave much more than mature controls, with no
clear fine-detail advantage. Faint parachute lines/dark analytic carriers
remain difficult. GFX foliage/fence remain noisy; RawNIND retains wavy fence
artifacts. Mature controls are smoother but retain detail/color limitations.
Neon/platform content differs in the ISO100 capture, preventing real-GT scores.
All full GFX outputs are101.995852MP; restore times50.6951/53.7366s miss10s.
These are single frozen legacy2-grid restores, excluding decode/export, not
repeated/corrected-grid/compiled benchmarks.

The separate actual-trained CUDA Inductor study rejects its first no-DINO
photo gate: max23.1481/20.7724DN16 and RMS4.8057/4.3343 versus fixed1/.25
bounds. State bytes/keys/parameter IDs stay unchanged. The worker did retain
both eager/compiled F32 arrays; independent NumPy64 reductions of all393,216
values exactly reproduce the runtime differences. The eager/IEEE-FP32 figures
are producer diagnostics, kept separate. Viewed all four source triplets in a
native eager/compiled comparison. No serving,DINO or full compiled run followed
rejection; there is no trained full-frame compiler-speed result or adoption.

The corrected-gridv2 numerical workflow subsequently completes and its owner
exits; its separate manual review/report remains to do. The CPU fresh-coordinate
diagnostic automatically resumes and reaches144 updates/arm, with0/64/128
evaluations present. Its256 endpoint remains pending. No protected-final scene
is scored and no production weights/noise profile/default compute policy changes.

Published19 exact quality-image copies plus two compiler triplets, full result
JSONs and the complete40k report. Main README now leads with the current status
and working V43, keeps its four representative images, and leaves detailed
history in docs. Updated the experiment index/requirements/architecture/learning
notes and completed compiler result. Image hashes, report links and diff checks
pass; no new product code or tests were needed for this read-only analysis.
The full SOTA/real-superiority/100MP-within10s objective remains unmet/unproven.
