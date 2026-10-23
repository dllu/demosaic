# Add configurable reconstruction smoothing with exact default replay

Recorded: 2026-10-23T14:17:46-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress: 108 fixed-V102 restorations and
324 output-gradient checks established a smaller-smoothing training hypothesis,
while cleaned Tiny/Small CPU/CUDA preflights completed. This turn implements
that hypothesis as a configurable training setting while original V104 runs.

Add `reconstruction_charbonnier_epsilon`, default .001, to ordinary
synthetic Commons/native reconstruction. It controls camera-linear, rendered,
spatial-gradient and auxiliary Charbonnier terms. Values must be positive with
a finite normal FP32 square. The trainer serializes the validated value and
rejects resume with a changed one; missing legacy metadata selects .001.
Ordinary and grouped mixed-domain paths both propagate it. Inference and model
parameter layouts are unchanged.

Inspection finds paired RAW already uses epsilon .0001. Keep that separate
loss unchanged, along with interval and noise-normalized sensor penalties.
Under image-log-MSE, the primary terms stay fixed and only the remaining
Charbonnier reconstruction terms use the option. This scope keeps the current
synthetic-source hypothesis distinct from changing measured noisy references.

The focused CPU suite passes 139 tests in 31.21 seconds, without skips. It
checks independent F64 penalty derivatives, masks and invalid values; grouped
domain gradients; specialized-penalty isolation; actual checkpoint metadata,
legacy fallback, resumed training and changed-epsilon rejection. Ruff checks
pass. One test's keyword-only dict construction is subsequently changed to
an equivalent literal for lint, without changing the tested behavior.

A namespace-isolated copy of the archived loss implementation independently
replays all 108 cached cases at .001/.0003/.0001. All 324 loss values, term
values and complete output-gradient tensors match exactly: 63,700,992 gradient
elements. Earlier saved gradient norms and directional derivatives also match;
no neural forward, training, RNG change or CUDA initialization occurs in this
replay.

Actual discarded CPU native64/B1 runs start from original V102 final20k EMA on
the cleaned 90,864-source recipe. Eight new-default updates reproduce the
archived trainer's model/EMA/Adam, Python/Torch RNG, step/best and all logged
values except elapsed time exactly. All eight input hashes also match a
separate .0003 continuation, whose 89 trainable model tensors change relative
to control. These are implementation fixtures, not quality endpoints.

The first mature resume fixture mistakenly requests eight additional updates
after the partial four, producing step12. Preserve that worker, its result,
the failed comparison and an explicit duration-error receipt. The independent
comparison catches the mistake rather than accepting a near match. A concurrent
observer had preserved the actual step4 checkpoint before `last.pt` replacement;
its hash matches the original partial reference. Resolve that historical
mutable reference to the exact retained snapshot without rewriting its receipt.
The corrected separate fixture resumes that step4 state for four additional
updates, requires step8 explicitly, and then matches the uninterrupted .0003
run exactly in model/EMA/Adam/Python/Torch RNG/step/best. A changed-epsilon
resume is rejected before any learned forward. No library change is needed
for the fixture correction.

[Implementation/default/resume closure](../docs/results/reconstruction-epsilon-implementation-v1.json) ·
[Current option and loss diagnostic](../docs/loss-smoothing-detail.md#configurable-training-scale).

The original V104 source, data and queues retain their bytes, as do the
unlaunched V109/V110 capacity preparations. Their loss stays fixed. Review
V104's completed endpoint before choosing the next baseline; a subsequent
loss comparison must keep data, initializer, architecture and budget matched
and report actual image metrics and native noisy/restored/GT triplets. Lower
training loss values from a changed penalty do not establish better quality.

The implemented .0003 setting also completes eight discarded CUDA updates
from original V102, at native256/B16/configured BF16. Initial91 EMA tensors
and official Tiny state hash match; all91 model/EMA tensors and89 Adam states
remain finite at step8. Commons/synthetic, native-RAW and paired-RAW domains
all execute. Reported peak allocation is6.95GB. These overlap V104 and another
GPU user, so timings are not throughput evidence. This is additional
implementation qualification, without a trained quality conclusion.
[Actual CUDA closure](../docs/results/reconstruction-epsilon-CUDA-v1.json).

V104 is confirmed live at19,275/20,000 after these checks. Its exact source,
training manifest and three dependent evaluation/export/detail queues remain
unchanged. The best completed quality model remains V102 until the new final
outputs are assessed; the broad project goals remain unachieved.

Final verification checks21 distinct referenced files against SHA256 across
the two new public receipts,127 local documentation links and all original
production/evaluation/capacity frozen plans. Ruff lint/format and whitespace
checks pass. Existing machine receipts, manifests, model files and prepared
capacity inputs retain their bytes.
