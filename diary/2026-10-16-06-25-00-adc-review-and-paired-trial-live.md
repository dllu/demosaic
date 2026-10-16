# ADC review complete; matched paired-data trial live

The frozenbf665d4 ADC-export workflow completes after400 CUDA tests and actual
genuine-weight preflight. Seven-condition photo34.974889 versus parent34.899343
(+.075545dB), SSIM+.000560; procedural+.203922dB with SSIM−.000731. It performs
zero training updates and keeps V43's learned tensors exact. All10,632 positive
noise model-case metrics,162 real paired crop metrics, and both parent/export
full GFX linear16/sRGB16 arrays match exactly. Eight RGB16 files and40 native
triplets verify. Published full report; opt-in only, no real-noise/alias/SOTA gain.

The paired-data controlled workflow starts in frozenb62c996 only after actual
ADC-owner exit/success. All451 CUDA tests pass in45.09s. Genuine V43 parent,
control32 versus expanded71-group batches at B16/native256 perform two discarded
BF16 AdamW updates each: finite loss/gradients, unchanged pinned DINO, identical
common initial tensors/FP16 prediction and exact portable FP16 reload. Numeric
loss logging emitted a harmless requires-grad-to-scalar warning; main helper
now detaches that scalar, without changing the frozen executed version or math.

Controller PID2391211 is live, control V53 first then V54. Identical retained
V43 step2000 EMA, fresh optimizer/EMA, seed52 B16 LR3e-5/planned4000 first1000;
only paired manifest changes. All logged nonpaired observations must match.
Full paired/427/procedural/GFX review and immutable snapshots follow. The
reviewed opt-in dataset contains83 IDs/71 groups/166 pairs/1492 crops, retaining
every original case/crop hash. No trained improvement is claimed yet.

The main real-photo checkpoint and README crops remain V43. Full objective
stays active: substantially better real output/SOTA, protected-final assessment
and10-second inference are not proven by these conditional/data improvements.
