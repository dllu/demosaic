# Trained global memory contribution

Recorded: 2026-10-27T18:07:14-07:00 (America/Los_Angeles).

Previous goal turn made concrete progress:40 new source inspections, two
future-only exclusions and one mixed white-plumage annotation, producing the
prepared90,774-photo/36-region bank and2,003-ID ledger in7b457ea. This turn
verified the original V131/V125 workers live, initially at2,425/1,500. V138's
original controller remained live waiting for V125 completion. Broad SOTA,
real RawNIND superiority, weak-detail recovery and100MP/10s remain unproven.

The completed V137 review has tiny ordinary/shadow changes, a small faint-ADC
gain over V136 and no clear mesh recovery. Stronger query/key adaptation alone
does not show whether trained memory contributes substantially. The earlier
normalized-attention mechanism used an untrained operator counterfactual with
V136 weights. This new diagnostic uses actual V1371k EMA SHA256
`5f7473dbd040326cdfb1a9cd326571388863024d789651cdc5194cb9d33229dd`, all18
branch tensors/18,272 parameters and four exact trained source modules.

Predeclared plan SHA256
`c8ca530d3e33fb21db1ca22ad7428eb7cca9631f390ae3a5cde64cade3aeaeb6`
selects the same six target-free branch inputs and already saved Rademacher
probes: first two Commons/native/paired members at steps1/2/5. Their earlier
CPU stabilization/span is reused, not asserted bitwise original GPU activation.
For each input, run one trained branch forward/backward and one fixed ablation
that replaces write_out's output with zeros after attention computation. Full/
ablated attention arguments, weights and attention outputs remain exact.
This removes memory write plus its nonlinear feed-forward influence while
retaining the local bypass and every weight.

Actual totals:12 branch forwards,12 backwards,24 softmaxes, zero root/CNN/DINO/
VST calls, target reads, new noise/RAW/optimizer work. Collection took9.26s,
without an inference-speed claim. Weights and Python/NumPy/Torch RNG remain
unchanged; CUDA remains uninitialized. Retain all12 offsets and gradient arrays,
all read/write Q/K/V and output arrays, and50,331,648 attention weights.

Removing trained memory changes0.830/1.159/1.390/1.078/1.253/1.390% of full
branch-offset RMS across the six contexts. Write entropy/logN is.893–.915;
returned context has centered-spatial/RMS.58–.84, so attention/memory is not
uniform, but the local feature path dominates this particular branch output.
This ratio is not an additive energy fraction or a measurement of downstream
RGB effect; the untouched CNN can amplify small feature changes. Twelve
memory-path tensor gradients become exactly zero under ablation. Fixed
Rademacher probe gradients are not reconstruction-loss gradients or evidence
of useful learning. Six deliberate contexts are not independent photo replicates.

The first NumPy audit rejected3/2048 near-canceling weighted sums at its strict
2e−8 absolute output tolerance, maximum offending error8.08196225e−8. Preserve
its source/policy/log. The explicit second audit separates independently
checked softmax error from an analytic FP32 dot-product error bound based on
key count and absolute products, plus FP64 allowance; no fitted wider near-zero
threshold or measured-forward replay. The original criterion is not claimed
passed. Independent checks cover18,272 trained state values,50,331,648 weights,
3,158,016 attention outputs,50,331,648 offset values,219,264 gradient values and
354 scalar fields. Maximum weight/output discrepancies are9.19e−8/3.16e−6;
maximum output-error fraction of the analytic bound is.06452, scalar reduction
error2.94e−15. This does not independently differentiate the full backward graph.

Created a separate, prospectively frozen V138 companion, policy SHA256
`d47b275d56adfafff73e13057233225669ced675cc857578ac0b0b022d0b7b04`.
Its live owner is3044042/create1793149563.82, waiting for original V138 primary
and faint reviews to finish and exact owners to exit. It reuses verified
109-EMA/18-Adam/frozen-parent/67-source endpoint proof and the same six inputs/
probes. Only12 new branch forwards/backwards and24 softmaxes are allowed; all
V137 controls are reused. CPU40GiB admission,32GiB runtime floor,600s measure
and original V138 faint absolute deadline1793761357.0 remain fixed. No full-root/
DINO/noise/RAW/optimizer work, automatic retries or existing schedule/budget/
owner changes. PYTHONDONTWRITEBYTECODE=1 preserves frozen bytecode. Child timeout
cleanup applies only to the new companion's own child.

The recent structural-guided JDD paper was rechecked. It describes DINOv3 plus
conditioned SwinIR, but its linked Calista-pedi/SG-for-JDD repository returned404
through web and connected GitHub metadata access on2026-10-27. The valid API
response is saved; no external code or weights were acquired. This is a dated
availability observation, not permanent absence. Existing independently
implemented branches remain distinct from a reproduction of that paper.

Published [the feature-mechanism report](../docs/global-memory-contribution.md),
six-context and216-gradient CSVs, numerical/call-budget evidence and current
README/model/research/training guides. V120 remains the general recommendation;
V138's real quality and larger-update memory effect remain unmeasured. Read
the future diagnostic alongside its native/GFX quality before choosing further
architecture changes. The full427-photo PSNR history and selector stay unchanged.
