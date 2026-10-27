# Start matched shadow-exposure training pilot with fixed native review

Recorded: 2026-10-26T22:13:46-07:00 (America/Los_Angeles).

Started a matched1,000-update shadow-data pilot from completed V120 Small EMA,
seed70,90783-source/23-region bank, native256/B16/BF16/single noise view,
LR1e-5/warm100, zeroPSF, paired32/native128. Both arms use a.5 reviewed-ROI
quota to exercise the policy; V126 shadow fraction0 and V127.5. This focused
quota differs from the original full-run5% recipe. Original V122/V123 and queued
V124/V125 sources, parents and budgets are unchanged. V120 stays the general choice.

All four CPU128/B1 and CUDA256/B16 checks completed16 fresh plus2 resumed
updates:72 training/encoder/optimizer calls,612 contexts,510 simulated and102
real paired observations. Thirty targets use shadows. All91 model/EMA tensors
and89 Adam states finite at18; eight changed-policy/fraction resumes rejected
before construction. Independent prep/state checks pass:46,301,184 unchanged
target values,86,264,514 native/paired bypass values and31,948,800 variances exact.
CUDA peaks7,041,804,800/7,043,878,912 bytes under16GiB.

After RAM fell below64GiB, adopted the three completed checks with the same
worker plan and inputs. New launch floor52GiB accounts for cap16+host4+reserve32.
Original pending-CUDA wait deadline,32GB runtime floor and all worker wall/update
budgets stay fixed. Only the new pilot's idle controllers were retired; no neural
step was repeated. V126 fresh training is live; V127 follows. The new quality
controller is queue-v3, bound to training-pilot-v2; worker artifacts stay in v1.

Prepared64 held-out observations: four targets ×gains1/8,1/32 ×ISO6400/12800
priors ×four CFAs. V120 completed64 genuinely new input forwards; all old controls
reuse saved predictions. Exact scaling/inverse display, ADC and variance pass.
Independent FFT/color proof verifies64 score rows/848 fields and7,372,800 PNG
channel values. Actually viewed two native160 noisy/V120/exact synthetic GT
triplets; bark softens and weak fur is almost lost under the severe shadow case.
These are current V120 outputs, not a new-model gain. The endpoint queue adds86
new calls each for V126/V127, including retained materials, mainGFX512 and both
extra3842/3835 mesh profiles. Broader427/camera/color/fullframe scope is not this pilot.

Preserved setup failures: the first whole-JSON heldout screen matched catalogue
metadata, while actual rows excluded the two native sources. Adopted its32
observations without resampling, then generated32 more. Queue-v1 lacked a frozen
helper and exited before its controller claim; v2 froze dependencies and passed
an actual frozen-entrypoint fixture before retirement for the handoff. The first
handoff hit asynchronous SIGSTOP status timing, resumed the idle controller and
retired none; corrected handoff waits for stopped status. All partial evidence
and original plans remain local. No original project owner was signaled.

All34 focused tests and Ruff pass. The updated reporter reproduces old V123
48 rows/12 summaries/24 PNG bytes exactly with no inference. Current docs now
show the23-region pilot as running while its byte-bound preparation label stays
unchanged. [Pilot, baseline table and crops](../docs/reviewed-shadow-training-pilot.md) ·
[Execution receipt](../docs/results/reviewed-shadow-training-pilot-setup-v1.json).
