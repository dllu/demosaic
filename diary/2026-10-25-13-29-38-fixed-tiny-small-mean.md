# Fixed Tiny and Small prediction mean does not resolve detail loss

Recorded: 2026-10-25T13:29:38-07:00 (America/Los_Angeles).

While V119 continues its original training, evaluated one prospective fixed
50/50 output mean of V115 Small and V117 Tiny. The rationale was their different
camera/photo strengths. Coefficients were declared before new operator scores;
there is no sweep, target fitting or neural inference. Arithmetic is native
FP32 camera RGB before clipping. This is an output operator, not a V120 trained
checkpoint or architecture change.

All five numerical stages complete: 14,190 observations / 4,450 saved batch
means. Inputs and exact target/WB/matrix values match across components. The new
archives preserve means and supervision. Photo PSNR is 37.0240837617dB:
+.0443531425 versus V114 and +.0470798659 versus V115, but −.0199975362 versus
V117. The last fixed-source interval is [−.02209808,−.01806790]dB; only 33/427
source means rise against V117. Camera means are 54.3138661131/54.0019499866dB,
slightly below Small in both panels. Capture/scene aggregation and bootstrap
scope match the existing component audits.

ADC mean/worst max-channel bias is 7.4307/62.7516DN16, above V114's
7.0806/51.7307. High-noise worst bias falls to 83.2949DN16, while mean bias is
17.5368. Centered spatial variation falls. Carrier gains for 4/8/16-pixel periods
are .00175590/.14502574/.71789039, averaged over four draws and four CFAs at
level .18/contrast .02/ISO12800. Four-pixel response remains nearly absent.

Viewed both exact-GT native160 noisy/mean/GT triplets and the direct five-column
material board. Bark's major fissures and canopy forms remain, with fine grain
and leaves smoothed. Viewed both five-column standing GFX boards covering all
six native regions. The fixed mean leaves foliage painterly and blue neon
markings flat; sky and fence/building geometry stay coherent. No clear recovery
of their shared missing detail is visible. These GFX means come from saved
FP32 crops of completed102MP frames, with the same+2EV/WB/matrix. The separate
ISO100 f/5.6 reference remains approximate, not GT; no pixelwise score uses it.

The first CPU attempt failed before computing any means: the frozen safety
module's authorized repository is its work directory, but the new archive path
was outside it. Preserved the executed sources, plan, log and zero-mean failure
receipt. The explicitly corrected v2 attempt places output under work/artifacts;
actual frozen layout/import checks pass. It finishes in 427.64s on two CPU cores
at nice10, without importing Torch. Every batch passes the independent unclipped
MSE decomposition with zero discrepancy. Maximum FP32 mean rounding is1.19e−7;
native stored NPY readback exactly matches component arithmetic.

This exposed the same future path issue in the already waiting native-camera
comparison. Created its archive link into its existing frozen work/artifacts
directory before any prediction or final checkpoint resolution. The actual
frozen safety module accepts the resolved destination. All67 frozen source
bindings and its original plan remain unchanged; controller3344479 was not
restarted. The reusable preparer now creates that layout directly. No V119
training or evaluation job is changed, and no original NN work is repeated.

Published the full measured tradeoff, two exact-GT triplets and all six GFX
comparisons. The mean does not combine the best component scores and does not
solve the intended real-detail defect. Continue the original cleaned-corpus
V119 run before choosing another training intervention. At13:32 local, the
original worker is live at logged step9,775/20,000. Quality remains the priority.

- [Complete fixed-mean report](../docs/fixed-tiny-small-mean.md)
- [Scores, source bindings and preserved failure](../docs/results/fixed-tiny-small-mean-v1.json)
- [Native images and metadata](../docs/images/fixed-tiny-small-mean-v1/manifest.json)
- [Completed native review and publication checks](../docs/results/fixed-tiny-small-mean-review-v1.json)
- [Queued native-camera output layout](../docs/results/native-camera-development-output-layout-v1.json)
