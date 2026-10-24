# Learned DINO fusion helps current restoration despite color-tail sensitivity

Recorded: 2026-10-24T00:46:30-07:00 (America/Los_Angeles).

Previous turn made progress by implementing and queuing the independent full
eight-view score audit. All eight exact training/evaluation/export/audit
handles remain live. V112 is continuing its original 20k budget. The overall
quality and runtime objectives remain open.

The proposed extra low-contrast source review was redirected after checking
the existing completed six-versus-32-region experiment, which found little
benefit from more regions. Saved V111/V112 monitor curves show small high-noise
gains; these eight-image monitors are not full quality results or a reason to
select an intermediate checkpoint. No source/data recipe was changed.

Ran a fixed CPU diagnostic on the original completed V104 and V111 EMAs:
zero only context.gates.0/1/2, preserve the other 88 tensors and frozen official
Tiny, evaluate the original 12 photo/2 adverse-camera/6 GFX observations and
eight preselected analytic fields, then restore all 91 EMA tensors exactly.
The eight fields include both parents' original worst ADC cases. No training,
new noise draw, CUDA, RAW decode or original-checkpoint mutation.

Actual neural/encoder forwards total 74: 56 intervention cases plus 18 original
replays (one photo and eight colors per parent). V104 anchors replay within
7.75e-7 camera units; V111 anchors are bit-exact. Independent Torch64 arithmetic
rebuilds all 424 NumPy64 score fields, maximum PSNR difference below 1.5e-14dB.
All saved predictions remain available.

Zero gates lower mean photo PSNR in every condition, with nine of twelve
individual cases regressing for each parent. ADC/ISO100/ISO12800 mean changes
are −.27553/−.01100/−.01473dB for V104 and
−.18535/−.01087/−.01644dB for V111. Both selected adverse-camera scores also
fall: about .47–.52dB for V104 and .33–.52dB for V111.

The original worst ADC biases improve from 1,218.06 to 335.51 DN16 for V104
case1008 and 2,142.98 to 1,505.66 DN16 for V111 case787. Large errors survive
and several other selected colors worsen. This identifies sensitivity to the
fusion intervention, without isolating a unique cause or comparing against
a model trained without DINO. Keep learned fusion in useful current models;
a later capacity trial should retain the useful original parent as a reference
alongside its common-function initializer.

Actually viewed all 112 native board cells. Bark/canopy and all six GFX regions
look close; there is no compelling recovery of fine foliage or saturated-light
detail. Camera blotches persist. V111's bright-gray green cast diminishes but
remains. Four diagnostic native noisy/zero-gate/exact-GT triplets are retained.
GFX ISO100 and camera AHD references remain explicitly nonexact.

The first renderer treated already-cropped GFX references as 512-pixel arrays
and stopped before completing the boards. Its source/log/partial files remain.
Renderer v2 uses the reference array's native [0,0,160,160] ROI with the same
original capture coordinates and display transform; no neural rerun or score
change. All completed board pixels read back exactly.

The worker's initial Ruff check flagged synchronous loop-closure captures and
the later del model; the shell lacked fail-fast and continued the authorized
CPU run. The actual per-model 37 root/encoder counts, removed hooks, exact gate
intervention and exact state restoration all pass. Executed source remains
unchanged, including those lint warnings; no production Python code changed.

[Current diagnostic and native comparisons](../docs/fusion-gate-quality.md) ·
[Complete source/state/arithmetic/native evidence](../docs/results/fusion-gate-ablation-CPU-v1.json).

