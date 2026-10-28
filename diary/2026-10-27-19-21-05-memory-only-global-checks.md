# Memory-only global RAW branch and genuine implementation checks

Recorded: 2026-10-27T19:21:05-07:00 (America/Los_Angeles).

The previous turn made progress by publishing the original V1252k crop review:
its monitor gain did not resolve weak detail. Revalidated the original V125/V131
workers and V138 waiting owners. The broader PROMPT.md quality/speed goals remain
unproven; V120 remains current.

Implemented explicit `memory-only-v3` global RAW features as a new V139 prototype.
The trained V137 memory-removal diagnostic found the direct local branch
dominant on six contexts. The new variant removes the direct content residual
and local feed-forward path so the returned branch offset passes through both
normalized attention operations. This tests a hypothesis, not a proven cause
or quality improvement. V138's existing normalized operator and all old frozen
jobs remain unchanged.

Removed `up.weight`, `down.weight`, `ff_gain`:15 tensors/14,144 parameters remain,
with the exact shared deterministic initialization. The zero projection preserves
the parent initially; bias-free values retain exact zero for per-phase spatial
constants after adaptation. Explicit mode selection and early resume rejection
prevent silently applying this changed operator to old learned weights.

The focused78-test suite passes independent NumPy attention arithmetic, absence
of the direct bypass, constant fields/all CFAs, batch/layout behavior, gradients,
strict branch reload, frozen-parent EMA updates and mode guards. The first dense
test fixture incorrectly assumed16 memory slots; it was corrected to the existing
64 slots. No model behavior/tolerance or quality budget changed for that fix.

Prepared source-frozen CPU128/B1/FP32 and CUDA256/B16/BF16 checks, then executed
each once for16 updates plus a real2-update resume under the original1k horizon.
Both pass106 model/EMA tensors,15 Adam states at18, exact91 common parent tensors
in model and EMA, nonzero gradients for all15 branch tensors during the prefix,
and seven changed-setting resume rejections per device before construction.
The official frozen DINOv3 ConvNeXt-Small is loaded and verified. CUDA admission
met52GiB after CPU exited; peak allocation7,929,051,648bytes stays under16GiB.
Checks are discarded warmup prefixes, not peak-LR stability or quality results.

Independent artifact auditing forbids neural module calls. It checks263,464,044
finite saved state values at16/18 across both phases,162,944,388 prepared-array
values against saved V137, all36 recomputed batch hashes,4,259,840 initial
RGB/auxiliary values and540 gradient metadata fields. Clean hashes match, but
pre-preparation clean arrays were not separately retained. Backward derivatives
are not independently rederived. All68 trained source modules match the frozen
snapshot. Against the original67-module V138 snapshot,64 files remain byte-exact;
the three other AST changes are confined to operator constructors/resume validation.

The repository check-driver import spacing was lint-corrected after preparation;
its frozen executed copy remains unchanged and has the same AST. This does not
change the68 neural source files or the check receipts.

V139's future1k recipe changes only the operator against V138: frozen parent,
LR1e-3, seed70,90782/27ROI and50% quota remain matched. V137 supplies retained
input/zero-initial-output controls, without old inference replay. The newer
90774/36 data bank stays separate. No V139 production controller or image-quality
collection is launched; a longer comparison must include V138, ordinary/faint/
shadow material, two native GT triplets, main3879/3880 and corrected3842/3835
mesh/JPEG comparisons. Original schedules, queues, selector and primary history
remain unchanged. Refreshed current research/training/README guides accordingly.

[Implementation and limits](../docs/raw-global-memory-only.md) ·
[Check receipts](../docs/results/raw-global-memory-only-checks-v1.json) ·
[Publication verification](../docs/results/raw-global-memory-only-publication-v1.json).
