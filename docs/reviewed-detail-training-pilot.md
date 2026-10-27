# V129: curated photographic-detail data pilot

**V129 tests the newly reviewed90,782-source/27-region cohort against the saved
V1261,000-update control. Quality is unmeasured.** The [V128 feature-loss pilot](v128-feature-pilot-quality.md)
found no useful gain, so V129 retains V120's architecture and reconstruction
loss with the optional feature and shadow terms off.

[Recipe](../configs/quality-v120-reviewed-detail-pilot-v129.yaml) ·
[Source decisions/native views](v123-source-review-through15800.md) ·
[27-region catalogue](../configs/low-contrast-training-rois-cleaned90782-v1.json).

The data change withholds one frame dominated by a flat advertising poster and
adds inspected fox fur, feather, thin iron fence/foliage and timber contexts.
All23 preceding region objects remain exact. Validation/test lines and private
GFX holdouts remain unchanged. The catalogue's original preparation-status text
is frozen because the plan binds its bytes; actual pilot status is recorded separately.

V129 and V126 share the V120 EMA parent, seed70, reviewed-region fraction.5,
native256/B16/BF16, single noise view, zero optical blur, paired32/native128,
LR1e−5,100 warmup steps and a fresh1,000-update budget. Commons inputs intentionally
change with the new membership/bank. Every native and paired clean/noisy batch
must match the retained V126 receipt; the domain schedule remains477/262/261.
This is a combined cohort/region-bank intervention rather than an isolated
estimate of the one-source exclusion.

Actual clean-reader preparation visits all27 regions and verifies common
targets. New discarded CPU128/B1 and CUDA256/B16 checks each passed16 updates
plus a two-update resume, with finite91 model/EMA tensors,89 Adam states and
all9 native/paired input hashes exact in each phase. Commons inputs deliberately
differ. [Actual check receipts](results/v129-implementation-checks-v1.json).
Fresh production is running. Plan budgets are36 check
updates plus1,000 production updates,30minutes/check and8hours production, with
no automatic retry/reset. Admission is52GiB, CUDA cap16GiB and runtime floor32GB.
V126 training/checks/predictions are reused; no control is retrained.

Training plan/status:
`.cache/current-quality-20261023-v1/reviewed-detail-training-pilot-v1/run/`.
The quality queue at
`.cache/current-quality-20261023-v1/reviewed-detail-quality-pilot-v1/queue-v1/`
waits for the exact1,000-update endpoint and then makes86 candidate restorations
on the same retained shadow/material/main-GFX/extra3842–3835 mesh inputs.
Independent scoring and actual native review follow collection. V123 and its
original dependent chain retain their budgets and inputs.
