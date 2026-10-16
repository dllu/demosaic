# First original fresh schedule completes 10,000 updates

After publishing the genuine ConvNeXt CPU restart audit and prepared CUDA checker
in 85fb19c, continued monitoring the live original workflow rather than treating
an observation timeout as completion or starting an overlapping GPU task.

No-context V45 completes its original 10,000-update schedule. Read and hashed
the stable final last.pt after its trainer exited. Verified global/planned step
10,000, every AdamW parameter state at 10,000, final group LR1e-5, explicit FP32
middle skip and original source bundle2f1a2251…ad01c. All403 logged losses and
gradient norms and all model tensors are finite. Final checkpoint SHA256:
`0df4ff404c38b8f4b42f6451486e91c97631544b1c817c126f371195942f3af4`.
It is still the terminal run last.pt; the controller will create the immutable
models/step10000 copy after all three arms, so that expected path was not created
early. No training settings or frozen source were changed.

The same controller164667, with matching process creation time, actually starts
the DINO-S continuation in trainer241003 from its immutable step3,000 snapshot.
First resumed step3,001 has LR8.224107109671586e-5 and the same observation hash
as no-context3,001. At publication S has reached3,200; all131 logged observations
match no-context. All122 historical observations still match across none/S/B.

[Boundary receipt](../docs/results/fresh-dino-capacity-no-context-10k-boundary.json).
This is actual training/state evidence, not a performance report, convergence
claim or model promotion. DINO-S/B and the full matched numerical/native/analytic/
102 MP GFX review remain. The unbounded objective remains active. The CPU audit
initialized no CUDA context; the deferred ConvNeXt GPU checks remain unexecuted.
