# Remove discarded physical-anchor construction

Previous goal turn: progress. It committed the inverse cleanup, completed and
independently audited the original4k control, and started the unchanged fresh
spectral arm. At this turn's start both exact owners620536/1792466470.15 and
628726/1792467113.42 were confirmed live, with spectralstep175; the complete
review/closure/reference/package and inverse-probe queues were also live.
No observation timeout caused a restart.

Found a second concrete discarded computation: physically anchored RGB models
construct full-resolution log-noise channels and concatenate21 channels, then
replace three channels with physical anchors and concatenate21 again. Build
the anchors directly in the initial concatenation. Unanchored paths, model
configuration, weights and channel order remain unchanged. Before editing,
checked that the live module is not an input bound to any active queue; training
and quality evaluation retain their archived physical source9018feb0… and old
VST355124a3… throughout.

CPU verification:116 pass/one CUDA-only skip in5.91s, covering all six fields,
input gradients, tensor strides, allCFAs/mixed noise families, flat/negative
inputs, normalization masks, supplied/computed RGB, autocast and both contiguous
and channels-last input layouts. Existing stabilized and normalization-augmented
model integration also passes. Ruff lint/format and diff checks pass.

The genuine V63 EMA checkpoint produces identical61,440 RGB values on four
cached GFX80×64 forward-only contexts; GFX/reference images never enter a
backward objective. Separate deterministic synthetic64×64 all-CFA fields yield
identical49,152 RGB values and all89 trainable parameter gradients, covering
32,904,704 gradient elements. No optimizer or update occurs; model bytes and
RNG remain unchanged. The first scratch run omitted the configured HF cache
environment; it was rerun offline with the existing cache. A second stopped on
a valid singleton gradient stride in the hash helper; hashing NumPy's canonical
C-order bytes fixes the observer without changing model calculations. Only the
successful v3 receipt is quality-independent engineering evidence.

CPU model receiptSHA1c3cb99e5242782aa6f78999770119680005bc6b7c136c32d14db82203a36537.
The four saved output files spanning the original model, inverse cleanup and
both physical policies all match SHA
425cc15ec6282b5caed94f64387efaf3e43d4608710094a122495ef8dc17dcad.

An actual native512/B4 CPU ATen census confirms two→one full-condition concats,
44,040,192→22,020,096 concatenation output elements, and3,145,728→zero log output
elements. Exactly84MiB of one condition-tensor materialization is removed per
batch. This is not measured GPU peak memory, time or full-model throughput.
Census receiptSHAcd67edacd550f36a221bdeff922e3eac9d7f3fbbaa99b214a8376f8a08b5e998.
The legacy physical function's AST matches the actual archived module exactly.

Frozen294 files/all46 candidate modules for a deferred CUDA component check at
`physical-feature-work-CUDA-v1`, planSHA
8e2e0fe8bd8b500c4731249c06be441760fbf65b1151b71671c7fcf146662dc9.
Actual owner636359/1792467919.07 is live and waiting for the exact prior inverse
probe622509/1792466628.84 to finish successfully. That predecessor already waits
for training, full quality review and native packaging. The new check compares
all six field bytes/strides at native64/512 in both layouts, then times only
the physical feature component. No new CUDA work runs alongside training, no
automatic retry/promotion or quality/full-frame speed claim.

At03:47UTC spectralstep925 was live with.968s/update; all previous evaluation
followers remained live and waiting. Full spectral4k,176 paired observations,
final RNG and complete numerical/native visual review remain outstanding.
PROMPT objective remains active; no new learned model is promoted and SOTA/
native superiority and100MP/10s remain unproven/unmet. Original photographs and
source spinning disks were untouched.

[Implementation/evidence](../docs/physical-feature-unused-work.md),
[CPU parity](../docs/results/physical-feature-work-CPU-v3.json),
[CPU serving census](../docs/results/physical-feature-work-serving-census-v1.json),
[actual deferred queue](../docs/results/physical-feature-work-CUDA-queue-v1.json).

At03:51UTC, independently audited the genuine retained spectral1k checkpoint
2fecc66dbb031102d57db6aa9bfe03c9cac7963defe96f5c6a4e66fe1d682a3e.
All93 model/93 EMA/91 AdamW states are finite, optimizer counters1,000 and second
moments nonnegative; original LR and20× head multiplier match. Head weight/bias
are nonzero in model and EMA. All56 observed dictionaries, saved Python/torch/
CUDA RNG states and41 scheduled metric domain/LR/source/supervision hashes
match the original control at1,000. The same exact fresh worker was live past
1,125; no additional training or inference was performed. ReceiptSHA
83304e082d7fc59642599c3321babc420332f423877b141994375ff5f11ddf37.
[Public retained1k audit](../docs/results/spectral-first1000-integrity-v1.json).
This is trajectory/state evidence, without a quality or promotion decision.
