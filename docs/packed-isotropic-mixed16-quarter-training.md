# Mixed16 continuation to160,000 examples

Both isolated continuations have completed after the
[complete32k-example quality review](packed-isotropic-mixed16-first32000-review.md).
V72 no-DINO and V73 DINO each stopped at10,000 updates/160,000 examples.
Their training workers and controller have exited. The
[complete matched quality review](packed-isotropic-mixed16-quarter-review.md)
is finished; neither is promoted and V43 remains the working reference. The
[completed-pair receipts and log check](results/mixed16-quarter-completed-training-CPU-v1.json)
and [independent full-state boundary audit](results/mixed16-quarter-training-boundary-v1.json)
record both endpoints and the actual handoff. The earlier
[first endpoint and actual handoff CPU audit](results/mixed16-quarter-first10k-handoff-CPU-v2.json)
retains its historical receipt snapshots and preserved no-DINO checkpoint.

The [selected no-DINO10k CPU preview](mixed16-no-dino10k-CPU-preview.md) now
includes two exact-GT photo triplets and all four standing GFX regions. It
improves over2k on those photos but trails the older equal-example RAW control
and remains grainy. The completed matched CUDA review is authoritative for
the full protocol.

The [frozen review](packed-isotropic-mixed16-quarter-review-queue.md)
passed its independent boundary gate after the exact training owner and final
child exited. All numerical, color, source-sensitivity, parent-progress and
artifact stages subsequently passed, followed by actual inspection of all146
native triplets/202 cells. The review owner has exited successfully.

Known/unseen-camera, full427-photo and analytic panels have now closed. The
[final photo crop match](results/mixed16-quarter-photo-crops-final-match-v1.json)
verifies that all16 previously inspected triplets exactly match the completed
full-photo report, including unchanged PNG/metadata bytes. Full GFX has also
closed; the [native inspection receipt](results/mixed16-quarter-GFX-native-view-v1.json)
records all24 triplets/32 unresized board cells at the standing sky, building,
foliage and fence coordinates. Both new arms remain grainier than mature
controls, with weak fine foliage/fence structure. The separate ISO100 image
is a qualitative reference, not GT. The [three-camera native inspection](results/mixed16-quarter-three-camera-native-view-v1.json)
adds24 triplets/36 cells from six cached Q2/a7RII/GFX50R contexts; its RawNIND
row is also not GT. The [selected-color inspection](results/mixed16-quarter-selected-colors-native-view-v1.json)
covers16 original/additional analytic triplets without new inference. The
[complete result registry](results/packed-isotropic-mixed16-quarter-review-v1.json)
binds these views and the completed hue/highlight boards to final reports and
unchanged original pixels. All twelve RGB16 exports pass artifact checks. The
decision preserves both10k states and selects analysis of the queued CUDA
profiles/EMA measurements before the next training budget; no extension was launched.

[Observed startup, plan/checkpoint hashes, exact owners and checks](results/packed-isotropic-mixed16-quarter-launch-v1.json).
The live status is
`/mnt/external/demosaic/runs/packed-isotropic-mixed16-quarter-workflow-v1.json`.

Each preserved2k checkpoint resumed with its current model, Adam, EMA and RNG
in a separate run directory and stopped at10,000 optimizer updates /40,000 original
B4 source groups /160,000 example draws. The original40,000-update /
640,000-example cosine horizon remains intact; this boundary is25% of that
horizon. It matches the older40k-B4 models' example budget. All2k archives and
logs remain unchanged.

The frozen production worker keeps gain32/residual÷32, IEEE FP32, four B4
forwards per optimizer update, LR2e−4,500-update warmup and adaptive EMA
capped at`.999**4`. Training retains the same Commons, native and paired
manifests. Additional downloads remain outside this experiment. GFX scene
siblings and protected-final captures remain excluded.

Actual CUDA startup checks verify all restored model tensors, Adam tensors
and parameter groups, and CPU/Python/CUDA global RNG before the first update.
EMA is compared with its parent before the first resumed EMA update. The next
16 actual256px training batches match the frozen source/noise fixtures exactly.
Both arms passed these actual startup checks. DINO child2884352/1792313905.76
and no-DINO child2645905/1792305192.6 have exited. Their first16
source/noise witnesses match each other and all16 independently rehashed
original fixtures. All403 final macro rows match across the pair in step, LR,
source groups, batch hash and example count. Each arm also matches403 overlapping
older RAW source/noise observations. The publication checker independently
rehashed completion artifacts and repeated these log comparisons without Torch.

The controller archived4k/6k/8k/10k states. No-DINO's endpoint SHA256 is
`d6e3bc6d98b1ffc294ac651c731636ef4072bef284925f357b690b78cc7fa9c1`.
DINO's is `64c5649a41669aa7e5276094278f3debb96b55174871c493ca380bf68ee3759f`.
The independent CPU check finds finite852 model/EMA/Adam states, every Adam
counter at10k, byte-identical portable loading of all852 EMA tensors, original
40k horizon and403 exact logged schedule/source/noise checks against older RAW
observations. The producer separately records exact portable FP32 output reload.
Both endpoints passed the reviewer's full-state/source/schedule boundary checks.
The DINO producer additionally records863 finite Adam states at10k, an unchanged
gradient-free official backbone and a bitwise-exact portable FP32 output reload.
The separate publication checker verifies these producer receipts; it does not
repeat tensor loading or inference. Full quality review is complete without
promotion; training has not extended beyond10k.

The first CPU checker reassociated the learning-rate formula, creating nine
one-ULP discrepancies. All403 recorded rates match the frozen trainer's actual
operation order exactly. The corrected checker uses that order with unchanged
exact equality; its failed predecessor and receipts remain preserved privately.

The [first no-DINO 4k archive CPU audit](results/mixed16-quarter-no-dino4k-state-CPU-v1.json)
passed at 64,000 examples while training continued. All 852 model tensors,
852 EMA tensors and 852 Adam states are finite. Every Adam counter is 4,000,
and LR is the original schedule's `0.00019653544138946785`. Portable CPU
loading reproduces every EMA tensor exactly. All 163 logged macro rows through
4k have the expected example counts/LRs and 163 matching older source/noise
observations. Both current and EMA tensor sets have changed since 2k. All
22 inputs/56 guards and the preserved 2k archive remain unchanged. This audit
checks saved state and portable EMA loading. The newer first10k audit above
does not replace that historical record or add another quality result.

The [DINO 4k saved-state CPU audit](results/mixed16-quarter-dino4k-state-CPU-v1.json)
finds finite865 model/EMA tensors and863 Adam states, all at4,000 updates /
64,000 examples. All11 trainable context tensors changed in both model and EMA
since2k and have nonzero first/second optimizer moments. The two preprocessing
buffers are unchanged; the reconstructed CPU backbone is frozen and in eval mode.
The original40k horizon, FP32 recipe and manifest hashes are retained. This
inspection ran no model forward or CUDA work. Active optimizer state does not
establish a useful DINO quality contribution; that requires the matched review.

The continuation driver and existing production mixed-loop integration checks
pass26 targeted tests; Ruff passes. The separate
[genuine-parent CPU restart preflight](mixed16-trained-state-restart-CPU.md)
also passes. The completed numerical/native review includes exact synthetic
noisy/denoised/GT triplets and cached GFX sky/building/foliage/fence views with
the separate ISO100 capture accurately labeled a qualitative reference.
