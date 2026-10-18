# Checkpointed experimental RAW/residual units

Added `isotropic_raw_gain` and `isotropic_residual_scale`, both default1. Only
four neural RAW features and the learned FP32 head residual are scaled. This
makes a future full-data trial reproducible through normal checkpoint/inference
APIs. Physical skip, output/loss units, metadata and capacity stay fixed.

Configured gain32/residual÷32 matches the discarded prototype exactly for
nonzero-head predictions, every gradient and three AdamW updates. Actual CPU
stop/resume preserves weights/EMA/Adam/Torch/Python RNG and rejects changed
units. DINO tests cover default/scaled initialization and nonzero-context
portable reload.68 unique focused cases are covered across targeted runs;
Ruff passes.

Actual no-DINO/DINO40k EMA defaults match archived code on64 frozen training
observations each/native34x50:652,800 RGB values bitwise equal. Nonzero heads
and96 nonzero DINO gates make the check nonvacuous; all852/1045 state tensors
remain unchanged. Published receipts bind current source/tests/fixtures/weights.
This is selected-context CPU FP32 compatibility, not new quality evidence.

At2048 example draws, scaled B4 Commons loss/MSE ratios are.93426/.77544 versus
scaled B16.94720/.85130; native/paired metrics remain mixed. The four GPU arms
and original CPU diagnostic continue unchanged. No batch selection, production
recipe change or promotion follows from the midpoint. Full quality goals remain
unmet/unproven.
