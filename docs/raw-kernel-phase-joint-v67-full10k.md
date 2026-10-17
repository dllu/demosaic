# Finishing the original V67 joint schedule

V67 is continuing from its fully reviewed step2,000 checkpoint toward the
original10,000 updates. It restores the training model, EMA, all92 AdamW states,
best value and Python/Torch/CUDA RNG. **This is the remaining8,000 updates of the
original schedule.** V43 remains the working reference; no final quality result
or promotion follows from the resume checks.

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

## Live training and final review work

Controller PID2949308/creation1792222522.64, trainer2949312/1792222523.48.
Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-full10k-workflow-v1.json`.
Immutable plan, source guards and logs:
`/mnt/external/demosaic/benchmarks/raw-kernel-phase-joint-v67-full10k-workflow-v1/`.
Verify actual PID/creation/state before acting; do not duplicate the run.

The controller finishes at10000, independently verifies94/94/92 and the exact
log/schedule/prefix protocol, preserves original2k guards, then freezes a new
checkpoint. Final evaluation still needs its owner-gated queue: original full427/
procedural/known/unseen panels, analytic carriers/flats, fixed hue grid, full GFX,
three cached cameras, selected CPU colors and artifact checks. Actual native views,
two exact-GT photo triplets and all four accurately labeled GFX regions remain
required before promotion. No protected-final model score or new training budget
is introduced by this continuation.
