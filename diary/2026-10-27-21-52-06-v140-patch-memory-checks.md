# Patch descriptors before global RAW memory matching

Recorded: 2026-10-27T21:52:06-07:00 (America/Los_Angeles).

Implemented V140 patch-memory-v4: retain the memory-only point embedding and
add a zero-initialized64→32 projection of eight neighboring signed-gradient
vectors. No center/border wrap or interpolation; all returned features still
pass through memory read/write. Adds2048 parameters,16 tensors/16192 total.
Shared15 initial tensors/RNG/point descriptors and zero parent response stay exact.
All-CFA constants remain zero after adaptation with variable variance.

Independent source proof:65/68 existing neural files byte-identical, selecting
constructor/mode changes restricted, common global forward exactly reproduces
its old AST after inlining the new point hook. New snapshot69 modules.
99 feature/scope tests and21 new handoff tests pass. Initial collection typo
named a nonexistent test and collected0; static audit first completed assertions
then failed serializing a string path. Original logs/source preserved; corrected
metadata, no training/control replay.

Genuine CPU128/B1/FP32 and CUDA256/B16/BF16 each complete16 fresh updates plus
actual2-update resume. Same original1k horizon/seed70/V120 parent/90782-27 data
as V139,91 parent model+EMA tensors exact,107 model/EMA and16 Adam states finite.
All16 gradient tensors positive; all2048 new patch weights nonzero in all four
saved16/18 states. Eight changed-mode/scope resumes per phase reject before
construction.36 root/encoder/optimizer calls and306 target slots. Initial outputs
match4259840 retained V137 RGB/auxiliary values; 68157440 zero offset values.

Independent no-neural-call audit checks263496816 finite saved values,
162944388 prepared values equal saved controls, all36 batch hashes and576 gradient
metadata values. Actual encoder/source checks stay exact; backward derivatives
not independently rederived. CUDA peak7995275776 bytes under12GiB cap. NewCUDA
admission50GiB/CPU40GiB/runtime32GB; original52GiB policies unchanged. Timing is
not a speed benchmark under concurrent training. Prototype quality unmeasured.

Queued a fresh original1000-update V140 run after all seven original V139 native/
faint/JPEG numeric stages and exact-owner exit, within V139's existing deadline.
Adopted both check receipts byte-for-byte; no check replay or resume18. New owner
3278427/create1793162937.3 waits for original V139 review.50GiB and128/208GiB
internal/external headroom stable15s,2h admission wait,12GiB cap,32GB floor,8h
worker. Same LR1e-3/warm100 and1000 input hashes must match saved V137. Existing
jobs/data/budgets/deadlines preserved. Original V125/V131 continue20k.

Fixed prospective102-input review support and612 adopted old/future predictions:
all V139 execution inputs including inherited V138 controls plus V139 output.
Seven-method expected672 metric rows/168 groups/64 native PNGs; faint420 strata/
224 decompositions and both GFX pairs+JPEGs, accurate nonexact references.
Dedicated endpoint binder/collector/report/audit/faint/JPEG automation is NOT yet
launched and remains next work; actual viewing/publication follows execution.
No restoration gain, full427/camera/color/fullframe/speed or broad superiority
claim. V120 selector and56 completed primary history points remain unchanged.

[Implementation and experiment state](../docs/raw-patch-memory.md) ·
[Checks/audits/queue evidence](../docs/results/raw-patch-memory-checks-v1.json).
