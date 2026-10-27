# V137 complete matched quality review

Recorded: 2026-10-27T15:39:01-07:00 (America/Los_Angeles).

V137 completes its full original1,000-update pilot and the102-input review.
Checkpoint SHA256 is5f7473dbd040326cdfb1a9cd326571388863024d789651cdc5194cb9d33229dd.
All1,000 clean/noisy input hashes match retained V136 before candidate forwards;
109 model/EMA tensors and107 Adam states are finite at1,000. The original
training horizon is not truncated or reset. Inference uses exact66-module
trained source, semantic modecosine-rms-v2 and the pinned official Small encoder.

Exactly102 new root/DINO forwards reuse306 old V120/V129/V136 predictions.
Weights, backbone and RNG stay unchanged; CUDA peak is9,356,368,384 allocated
bytes. Review adds no noise observations, RAW decodes, reference inference or
optimizer updates. Independent FFT/display audit recomputes384 metric rows,
96 summaries/5,700 scalar fields and every native cell of64 primary PNGs,
22,118,400 exact RGB channels. Maximum PSNR discrepancy is1.43e−14dB.

Against matched V136, ordinary mean falls.000541dB and the four shadow means
fall.000702–.004387dB. Faint ADC rises.033390dB, but remains.016964dB below V120.
The support is four material contexts/all four CFAs, one retained observation
per CFA/condition. It is not427 independent sources or broad camera evidence.
Selected ordinary band errors fall while fur/wood projected gains fall;
grass response rises only slightly. Native fine hairs/grass/wood remain soft.

The prospectively frozen four-method faint supplement completes240 original-
source strata,128 decompositions and four shared40× display boards. Its
independent audit checks1,843,200 exact PNG channels. Against V136, faint fur2–5%
improves in gain/error; weaker fur0–2% and wood lose gain with lower errors,
while grass worsens in both. Pooled sRGB MSE falls1.99048824e−7→1.96682133e−7,
and centered spatial MSE falls1.89603011e−7→1.85689562e−7; the ROI-mean error
fraction rises4.745%→5.589%. V120 still has slightly lower pooled total/spatial
errors overall. Forty-fold contrast is display only and never scored or fit.

A second zero-neural supplement was frozen before candidate quality outputs.
It reads original1k weights/EMA/Adam, deterministic initialization and CPU FP32
zero-gradient decay/EMA references, without claiming bitwise GPU optimizer
replay or image-quality causality. V137 write-query/key EMA changes are
4.89e−5/5.11e−5 versus V136's4.21e−10/5.17e−10. New training records56 exact
observation steps1–16/every25 through1,000; old V136 production maxima cover
only1–16. Independent reductions check720 state/Adam fields and1,008 gradient-
snapshot metadata entries, with max state difference2.14e−15. Raw gradient
arrays are not independently recomputed. This confirms stronger adaptation,
without resolving the quality problem. No extra branch/root/encoder forward
occurs in either metadata supplement.

Actually viewed all32 primary comparison boards, two exact synthetic-GT triplets
and four enhanced faint boards at original resolution. Larger bark structure
stays coherent; fine fur/grass/wood remain attenuated and deeper shadows retain
color blotches. Main GFX foliage stays painterly, larger fence/building geometry
coherent and sky quiet. Corrected DSCF3842/DSCF3835 fine mesh remains largely
erased nominally; nearby3879 conditioning leaves weak irregular diagonal texture
without clear new correct-lattice recovery. The left blue point persists.
Normal faint8-bit panels look almost identical; enhanced panels reveal residual
colored texture without a clear broad recovery. The other primary triplets are
pixel-audited subsets, not separately claimed viewed.

Publish26 exact native PNG copies,384 score rows,1,264 band rows,240 faint
strata,128 decompositions and18 learning-state rows. All four model checkpoint
hashes now accompany each public image alongside source/ROI/noise/display
metadata. Include two native noisy/restored/exact processed synthetic-GT
triplets and both main3879/3880 and corrected extra3842/3835 pairs. Binned
native-camera, ISO100/AHD and camera JPEG references are approximate, notGT.
Both pairs/JPEGs/siblings remain held out; originals and caches are unchanged.

A separate standalone PNG/SVG plot describes pilot mean-PSNR deltas by version
on this retained support, with20k parent versus independently initialized1k
pilots labeled. Verify all24 score points against the measured group means;
inspect the final plot. Preserve first/second renders and receipts while fixing
adjacent-version tick overlap and legend placement in a third render. No score,
image crop or neural work changes. Keep the full427-source history separate
at56 comparable completed endpoints.

Update README, current-model/research/training/experiment/index guides and both
GFX galleries with the measured gains and drawbacks. V120 remains the general
recommendation on actual evidence. No20k conditioned-global run is queued.
Stronger global adaptation alone has not recovered the missing fine photographic
detail. All original training/review budgets and owners remain intact. Broad
RawNIND superiority, state of the art, full V137427/camera/color/full-frame
quality and100MP/10s remain unproven; the full goal remains active.

[Quality report and native comparisons](../docs/v137-global-conditioned-quality.md) ·
[Execution/quality receipt](../docs/results/v137-global-conditioned-quality-v1.json) ·
[Score plot and preserved renders](../docs/results/v137-global-conditioned-plot-v3.json) ·
[Publication verification](../docs/results/v137-global-conditioned-publication-v1.json).
