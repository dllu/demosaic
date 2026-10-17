# Finishing the original V67 joint schedule

V67 has completed its **original 10,000-update schedule**. The controller and
separate primary state audit agree on finite 94 model/94 EMA/92 AdamW states,
all 402 log rows, the unchanged original source/data/recipe and the exact 2k
resume boundary. Final LR is 1e-5. Full quality evaluation and all28 actual native
views are complete. The [final performance review](raw-kernel-phase-joint-v67-full10k-review.md)
finds photo+1.36945dB over first2k but −1.95519dB versus V60, with weak-detail and
bright-color regressions. V43 remains the working reference; V67 is not promoted.
The sections below retain the earlier resume/queue protocol and observations;
the linked final review supersedes their pending quality status.

[Actual completed training/state audit receipt](results/raw-kernel-phase-joint-v67-full10k-training-completed.json).
Frozen final checkpoint SHA256:
`a37e6c84597de540440bbf29c93eb79c9ddbf74024b39843a2941143fe6470fc`.

[Completed2k performance/native review](raw-kernel-phase-joint-v67-first2k-review.md).
[Continuation recipe](../configs/dino-convnext-raw-kernel-phase-joint-full10k-b16-v67.yaml).
[Actual resume fixture, independent checks and launch](results/raw-kernel-phase-joint-v67-full10k-resume.json).

Only the output directory and experiment notes differ from the original recipe.
The new run is:
`/mnt/external/demosaic/runs/dino-convnext-raw-kernel-phase-joint-b16-v67-full10k`.
The original2k run/log/source, fixed checkpoint and all review files remain
byte-for-byte unchanged. The new log starts with an exact copy of the original
prefix; it retains the first resumed row2001 as well as the original25-step
logging cadence. The final audit expects402 train rows, including81 original
rows. It also verifies every learning rate against the original10k schedule.

The model/source/data/seed50/LR1e-4/warmup100/B16/native256/BF16/workers4+2+2,
fractions, palette, geometry, noise and validation are unchanged. DINO stays
frozen. Source bundle:
`fc0297db08d659523fdcefe1ef0e7a4da12ae97f648e95b1579db65de93d268a`.
Resume checkpoint SHA256:
`25d3bb57ff0588a804d161c957f28ebdcfc32e666bac37b52c35fd0b92de9b17`.

## Executed isolated-resume checks

A discarded25-update fixture uses the actual2k checkpoint and all production
settings, changing only its output directory/notes. Hooks on the real trainer
verify the original **model rather than EMA**, all92 optimizer states and initial
EMA exactly. All three RNG families match before the first data fetch. It starts
at2000 and ends at2025, exercises Commons/native/paired domains, retains the
original log prefix and source/recipe/schedule, and preserves the best value and
V66 initialization lineage. The actual DINO backbone hash remains exact, with no
gradients. Finite94 model/94 EMA/92 AdamW states all have optimizer step2025.
No fixture state is used as production initialization.

An independent CPU read verifies that real2025 checkpoint, all83 log rows,
original prefix, source/data/recipe/RNG and learning rates. Four corrupted log
copies—changed prefix, omitted2001, duplicate2001 and wrong2001 LR—are rejected.
The resume-aware auditor exactly replays the entire previously published2k
boundary. Actual production rows2001 and2025 match the fixture's input hashes,
domains and learning rates. These checks establish state restoration and input protocol,
not deterministic CUDA optimization, convergence or trained quality.

## Completed training and live final review

Training controller PID2949308/creation1792222522.64 and trainer2949312/1792222523.48
have both exited successfully.
Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-full10k-workflow-v1.json`.
Immutable plan, source guards and logs:
`/mnt/external/demosaic/benchmarks/raw-kernel-phase-joint-v67-full10k-workflow-v1/`.
Verify actual PID/creation/state before acting; do not duplicate the run.

The controller completed at 10000, independently verified 94/94/92 and the exact
log/schedule/prefix protocol, preserved original2k guards, then froze the final
checkpoint. The primary review has passed its separate original10000 state
audit and is running quality panels. Later stages retain their serial order. [Launch and executed CPU checks](results/raw-kernel-phase-joint-v67-full10k-review-queue.json).

1. Primary panels: an independent state audit at 10,000; 288 known-CFA cases,
   360 unseen-CFA cases and 49,616 full-photo/procedural cases; 896 analytic
   cases with an independent 1,504-field summary audit; full GFX with four native
   crops and two full RGB16 TIFFs; six crops from the three other cached cameras;
   and 32 selected CPU-color predictions with 192 audited fields.
2. Statistics and hue: 48 saved comparisons and 12 classical witnesses against
   the reviewed V67 first-2k checkpoint and retained V60/V58/V43 results; one new
   fixed hue grid with 1,176 predictions, 7,056 independently recomputed fields and 216
   summary scalars. Previous model predictions are retained, without bulk reruns.
3. CPU artifact audit: state/source/data/recipe/original log prefix and schedule,
   19 native PNGs, 23 float arrays and two full RGB16 TIFFs, with unchanged noisy and
   reference pixels and display transforms.

The primary/statistics/artifact owners are respectively PID 2969247,
2969624 and 2969626 (creation times and hashes in the launch record). At launch
all three are live, child-free and have produced no review output. Status files
under `/mnt/external/demosaic/runs/` use the common prefix
`raw-kernel-phase-joint-v67-full10k-` with suffixes `review-workflow-v1.json`,
`statistics-hue-workflow-v1.json` and `artifact-workflow-v1.json`. Verify actual
PID/creation/state before acting; do not duplicate them.

The new review gates replay actual completed V65/V66/V67 gates and entire saved
state boundaries exactly, including the genuine isolated 2,025-update resume boundary.
All 36 retained V67 comparisons reproduce; 12 self comparisons are exactly zero.
Actual pending training, primary and statistics owners reject downstream work
before output. All archived Python sources parse. The actual completed-training gate and separate 10,000 state audit now pass.
The earlier preflights establish review protocol; completed quality evidence
still requires the running downstream panels/audits. Queued tools and earlier source/data are archived and hash-guarded.

Actual native views, two exact-GT photo triplets and all four accurately labeled
GFX regions (sky/building/foliage/fence) remain required before a quality decision.
The 2k-to-10k comparison is progress along one original training trajectory;
it does not isolate architecture, unfreezing or seed effects. No protected-final
model score, new training budget or automatic promotion is introduced.

The [supplementary neon/platform check](gfx-highlight-qualitative.md) freezes two
additional input-only regions. A CPU follower waits behind successful final
artifact-owner exit, then evaluates only the genuine completed-10,000 checkpoint
and independently audits two native triplets. Their actual visual review remains
required. The original four standing regions and primary review queue are unchanged.

A [bounded inference profile](raw-kernel-inference-profile.md) waits behind the
supplementary CPU owner. Its real-model CPU hook/output check passes; genuine
CUDA attribution remains pending. It preserves the final checkpoint and all
inference settings, adds no training, and does not establish a new full-frame
speed or quality result.

The [final report assembly check](results/raw-kernel-v67-final-report-preparation.json)
replays the four actual completed first-2k workflow records and validates its
26 reviewed core PNGs plus two already-reviewed neon/platform PNGs. It rejects
missing views, changed hashes, duplicate images and resized panel metadata.
Invoking the final publisher against the actual live 10,000-step run rejects
publication before any final report or image is written. Its source is archived
in `/mnt/external/demosaic/benchmarks/raw-kernel-v67-full10k-report-preparation-v1/`.
The eventual positive publication path still requires all five final owners to
succeed and exit, the exact 402-row resume boundary, all audits, 28 new actual
native views, fresh visual notes and an explicit quality decision. The earlier
images exercise the assembly code only; they do not replace final-model crops.

Six new native panels have now been actually viewed, alongside their six
retained first2k counterparts: two exact-GT photographs, two known real pairs
and two unseen real pairs. All PNG/checkpoint/metadata hashes verify, and all
noisy/reference panel pixels match the first2k views bitwise. The real-pair AHD
panels remain auxiliary references, not exact RGB GT. The private actual-view
receipt contains six of the required 28 new images; GFX, analytic, three-camera,
CPU color and hue/highlight views and final audits remain required. These early
views do not complete the performance report or make a quality decision.
