# Complete V198 evaluation protocol

**Full training and its CPU audit are complete. Evaluation code is frozen, CPU
preflights and the four actual CUDA feature bridges pass, and the controller is
registered for both endpoints. No complete V198 image-quality result exists yet.** The
[architecture and training note](cfa-innovation-wave.md) explains the all-CFA
physical-wave representation and its limitations.

The new raw and EMA endpoints each run on the same **822 cached observations**
as V195/V197. This includes 256 present meshes, 256 matched absent meshes,
mixed scenes with genuinely quiet areas, fresh gray/colored flats, natural-photo
texture and ADC controls. Both protected GFX capture families remain qualitative
tests: main DSCF3879/3880 sky, building, foliage and coarse fence; fine cab
DSCF3842/3835, both ROIs and noise profiles, with the independently rendered
ISO100 and straight-out-of-camera JPEG references. None is a training input.

Each new forward must reproduce the frozen V195 Whole EMA, V183 EMA and V169
outputs exactly. The saved RGB result must equal the anchor plus the new physical
wave correction. Local zero-variance routing stays exact. Planned component
counts across both endpoints are **1,644 wrapper and frozen calls, 1,500 matching
network and projection calls, 7,500 sampler calls and 1,500 calls to each old/new
wave head**. There are 144 ADC-only endpoint cases.

The evidence stream records actual four-phase canonical order, selected bins,
nominal center powers, local affine-wave numerical ranks, support geometry,
24-channel contexts and physical complex RGB wave fingerprints. All measurements
depend on input RAW and the frozen anchor; raw/EMA states must reuse them exactly.
The independent CPU audit validates geometry and phase order and binds selector,
support, projected green powers and residual fields to the saved V197 innovation
journal. This checks the unchanged measurement components, without claiming that
the new representation is an isolated causal ablation.

Before running any new neural predictions, a registered CUDA measurement-only
worker verifies four actual cached feature cases: both predeclared mesh examples,
the main building and the fine cab context. It reads saved V195 predictions to
form innovation. Neural module calls are disabled in that worker. It must match
the earlier V197 selection, smaller support and projected green powers exactly;
it neither trains on these held-out inputs nor measures a new model's quality.

After the two endpoint streams terminate, a CPU audit independently recomputes
all available native metrics, RGB additions and wave RMS values, checks strict
raw/EMA endpoint state and verifies aggregate means. The design retains **36
native contexts per endpoint**, saving **72 RGB arrays and 72 wave arrays** in
compact encodings. The reducer combines **nine methods / 7,398 metric rows**:
V183, V187 and V195 EMA; all four V197 raw/EMA endpoints; both V198 states.
Individual paired changes accompany cohort means, including actual quiet,
blank, absent and fresh-flat errors. Real references are not scored as GT.

The controller then creates two strict standalone exports and computes the same
two directional examples with independent spatial projection checks. Native
figures retain V187's quieter output, V195, both V197 measurement EMAs and both
new states. Planned output is **48 comparison boards and 12 native triplets**.
All crop cells are 160×160 original pixels; identical coordinates, exposure and
contrast are inherited from the checked earlier displays. Two independent display
implementations verify prediction panels. No crop is resized. Source/ROI,
checkpoint, noise and exposure metadata remain attached to every comparison.

Actual viewing, browser source-pixel verification, report interpretation and
README updates follow the rendered outputs. A training loss, completion status,
aggregate response gain or engineering bound cannot substitute for inspecting
fine crossings, the building artifact and false flat-region texture. The current
[V197 strengths and costs](innovation-wave-comparison.md) remain the latest
completed quality evidence.

Preparation checks pass **13 measurement-record tests**, including altered
canonical phase, bin/rank, geometry, wave hash/shape and power/rank-count rejection.
The 36 saved anchor contexts reproduce **255 numeric metric values** within
`1e-10`. All **822 cached CFA layouts** are valid, and **64 existing exact-GT
panels / 4,915,200 RGB channels** match the declared display in two independent
implementations. All seven frozen stage entrypoints import without importing
Torch. These checks generate no new neural predictions.

The registered controller follows actual PID plus process creation time and
never restarts a prediction prefix because observation expires. Scientific
outputs, source and machine receipts remain immutable. The existing **2 GiB
total trial budget**, 40 GiB local floor and zero external writes still apply;
arrays and older galleries are reused in place. No new source/noise draws,
parent/DINO inference, RAW decode, original-photo or `/mnt/dataz` access occurs.

[Frozen preparation, preflights and controller evidence](results/v198-cfa-innovation-review-prepared-v1.json).
[Training audit and actual feature bridge](results/v198-cfa-training-completed-v1.json).

The private trial root is
`.cache/quality-20261108/V198-cfa-innovation-wave-trial-v1/`.
`quality-controller-v1/watch-status-v1.json`, its registered owner and later
terminal receipts are authoritative for progress after this preparation snapshot.
