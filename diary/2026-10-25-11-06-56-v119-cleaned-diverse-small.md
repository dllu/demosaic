# Start the cleaned and camera-balanced Small continuation

Recorded: 2026-10-25T11:06:56-07:00 (America/Los_Angeles).

Started V119 from the final V115 Small20k EMA, SHA256
`fee5d05c599cb32f5a1e587c31979f040a06152c8e14676481eee83a4ce04d84`.
Use the cleaned90,791 Commons sources, original-source-preserving sampling,
six reviewed ROIs and corrected83-ID paired extension. Preserve the original
camera probabilities instead of the expanded data's Sony-heavy uniform mix.
Native128 and validation manifests retain their exact parent hashes.

Retain native256/B16/BF16, zero optical PSFs,4×→geometry→area2, photographic
contrast attenuation.25, legacy weak.15/fine0, epsilon.0003 and paired.0001.
Band weight stays0 after the completed V117/V118 evidence. Seed65, LR1e-5,
warmup200 and a full20k budget start with fresh AdamW/EMA. This is combined
data plus additional training; no isolated causal effect is claimed.

Seed65's first native batch is step14. Both predeclared16-update checks pass:
CPU64/B1/FP32 and CUDA256/B16/BF16,11 Commons/four paired/one native each.
Each checks91 exact parent tensors, official frozen Small encoder,89 fresh
AdamW states, finite weights/EMA/optimizer, manifests and actual source archive.
No feature fit is repeated. Source snapshot SHA256:
`7edfbceae2e6363cd07e868720a3ea2ef7b386ffee7c2d6ad4b434bd629d429e`.

The original bounded controller is PID3125213, creation1792951326.78; production
worker PID3134902, creation1792951461.96. The initial publication retains the
complete log prefix through step200, with finite loss/gradient/LR and the first
loss exact to the discarded CUDA check. These are implementation observations,
without an improved-quality claim. Preserve all original sources and receipts.

Queued the full eight-stage single-endpoint FP32 review:4586 new model/encoder
calls and14190 primary observations, then independent NumPy64 validation. The
status adapter binds the original generic training controller and phase-accounting
receipts; it does not edit executed training code. Independent and matched
controllers import without Torch and add no inference during preparation.

Three saved-output comparisons reuse V115/V114/V117, with14190 matched primary
records and427-source/5124-case/96,075-GT-block natural detail each. Prepare two
native160 exact-GT triplets, all six GFX regions and exact checks of both RGB16
exports/460,800 native values. Actual viewing and interpretation follow the
completed results, then current docs/README should reflect useful gains and
remaining weaknesses. No parent/control neural rerun or automatic promotion.

[Recipe and scope](../docs/cleaned-diverse-small-training.md) ·
[Started-run/queue receipts](../docs/results/v119-training-start-v1.json).

