# Smaller multiscale measured-CFA loss

V62 completed its first **1,000 updates** and its
[quality review](sensor-mean-v62-first1k-review.md). Stop this **0.001** recipe:
photo PSNR ties the control, while SSIM, unseen-camera RAW and weak carriers
regress. Bright saturated-field bias improves but remains large. It follows the
[negative .01 trial](sensor-mean-v61-first1k-review.md); reducing optimization
pressure recovers accuracy but does not establish an improved general model.
The next separate comparison will isolate more reviewed Commons data and longer
training, without this loss; the
[longer matched data stage](longer-commons-data-stage.md) is now running.

[Actual launch, source/config/data hashes, CPU/CUDA receipts and logged-input matches](results/sensor-mean-v62-first1k-launch.json).
[Configuration](../configs/dino-convnext-palette-sensor-mean-small-b16-v62.yaml).
[Frozen whole-state checkpoint and all 41 matched logged observations](results/sensor-mean-v62-first1k-freeze.json).
[Serialized independent primary/state/native/hue review](results/sensor-mean-v62-first1k-final-review-queue.json).

The trainer exited successfully. Checkpoint SHA256:
`714aeb4abe26e03da8fc6e92c068be7b2070da74ece540e0612c2bd2e0215999`.
The final review reuses audited parent/V60/V61/nonlocal arrays and computes only
1,176 new V62 hue predictions. The shared score/artifact audit reproduces all
original V61 numeric and integrity fields exactly. A CPU-only replay of the
generalized grid wrapper reproduces 4,704 case/array/model records, 72 groups and
all 12 whole native PNG hashes, without inference. No quality decision follows
from these engineering checks.

The completed V60 first1k run is the control. Both initialize from the same
mature V58 step10000 EMA, SHA256
`cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3`,
with fresh AdamW/EMA, seed 48, batch 16/native 256, BF16, LR 2e-5, warmup 100,
original 4,000-update schedule and a first review at 1,000. Only the multiscale
loss coefficient differs from V60; run path and notes identify this trial.
V61's state and schedule remain untouched.

All 32,904,704 restoration parameters train; the pinned DINOv3 ConvNeXt backbone
stays frozen. The 8-stop smooth palette, Commons 40,170/native 128/paired 32,
fractions, noise/ADC, 4×→geometry/PSF→area2 and original 8× validation stay fixed.
The loss implementation and inference graph are unchanged. Reviewed 66,934-image
data and new 75,806-image candidates remain separate.

Executed CPU FP32/batch1/native64 checks match four uninterrupted updates to
two plus two resumed updates exactly in all nine whole-state fields and numeric
logs. Genuine CUDA BF16/batch16/native256 checks verify finite 91 model/91 EMA/
89 AdamW states, exact saved-step2 restoration and two exact portable EMA
predictions. All four fixture observation hashes match loss-off controls across
Commons, native and paired domains. Fixtures force smooth Commons and use zero
workers; they establish engineering behavior, not production quality or speed.

CUDA fixture preclip gradient norms with .001 were .707/.703/1.266/.330 versus
loss-off .465/.527/.051/.093. Peak allocation was 7.200 GB. Lower pressure than
the .01 fixture is not a prediction of model quality. The physical/reporting
suite passed 14 tests, with one CUDA test skipped under an explicitly hidden
CUDA environment; genuine CUDA behavior was checked separately above.

Trainer PID 1943479, creation 1792206257.22, owns the run. Its immutable controller
freezes source/config/data and complete state at 1,000 and requires all 41 logged
domain/LR/input hashes to match V60. Actual startup rows match. Review queue
PID 1944140, creation 1792206299.38, waits for that exact owner's exit before
starting primary photo/paired/analytic/GFX/other-camera/CPU panels. It reuses the
immutable evaluated operators and corrects the old analytic count to 896 rows.
Old V60 neural panels are retained for comparison. Hue-grid, independent
statistics/state/native review and a quality decision remain required afterward.

Operational status:
`/mnt/external/demosaic/runs/sensor-mean-v62-first1k-workflow-v1.json` and
`sensor-mean-v62-first1k-review-workflow-v1.json` in the same directory.
Inspect actual PID/creation/status before acting; do not launch duplicates.
There is no automatic continuation or promotion. Reports must retain native
triplets and all four standing DSCF3879/3880 regions with accurate non-GT labels.
Protected-final stays closed; SOTA, real-camera superiority and the 10-second
100 MP objective remain unresolved.
