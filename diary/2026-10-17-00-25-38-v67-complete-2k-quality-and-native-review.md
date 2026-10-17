# V67 first2000 quality review complete; not promoted

V67 stops at the declared2000 boundary on its unchanged original10000 schedule.
Frozen checkpoint25d3bb57ff0588a804d161c957f28ebdcfc32e666bac37b52c35fd0b92de9b17.
Actual training controller/child exited; primary v2, statistics/hue and artifact
owners also all exited with completed statuses, verified by PID/creation. Both
controller/independent primary state checks and final artifact audit pass94model/
94EMA/92AdamW finite, all92 restoration parameters changed, two normalization
buffers exact. Source fc0297 rebuilt from archived bytes; original manifests,
recipe/protocol/RNG/81 logged learning rates pass. Last LR9.206544616434248e-5.
Actual DINO remains frozen by source/optimizer/preflight evidence; it is excluded
from restoration checkpoints and not independently observable from those alone.

Independent50,264-case statistics,48 comparisons and12 classical witnesses pass.
Photo32.33964/.927021, procedural29.65301/.917090, known/unseen measured-CFA
52.02905/50.68634. Versus initialized V66: photo+2.81345dB (source95% interval
[2.75571,2.87272]), procedural+1.62347 ([1.37134,1.87527]), known+6.07209 and
unseen+7.01233. Versus mature V60 all primary means remain lower; photo−3.32464dB
[−3.43423,−3.22633]. Scope/seed/LR/history/budget differ, not a causal unfreezing
comparison or convergence result. Protected-final model scores remain unused.

Actually viewed all26 new native PNGs:6 paired/photo early,3 analytic,4 full-GFX,
6 additional cameras,4 selected CPU colors,3 hue. Less grain than V66, but missing
cords, noisy/soft truss/leaves/fence and color variation remain. RawNIND is only a
comparator; separate ISO100/AHD reference differs in aperture/time/motion, not GT.
Eight unchanged PNGs in the human report include two exact simulated-GT photo
triplets, all four standing GFX regions, one carrier and one hue. Original source/
ROI/conditioning/checkpoint/display metadata retained, no crop resizing.

New generic analytic audit passes896cases/56groups/1504scalars (2.22e-16max error),
scalar coverage/arithmetic only, not unavailable full-prediction recomputation.
High-noise carrier gains fall to.14283/.44832; unrelated residual RMS also falls.
Neutral spatial luma RMS.004272 versus V66 .013338/Malvar .020780. Hue1176new
predictions/7056Torch64fields/216group scalars pass; no old array merge, source
records exact to retained V66/V60. At highnoise/peak.9 mid-saturation bias/RMSE
.002239/.009605, high-saturation .001027/.008279. Bias rises versus V66 while RMSE
falls, so physical clean-constant invariance has not guaranteed noisy unbiasedness.

Two full101.996MP RGB16 outputs,19primaryPNG/23F32 arrays and four exact full-TIFF/
native-ROI comparisons pass. Eighteen three-camera rerenders differ in just3
channel values byone8-bit code within unchanged preview-only bounds. Shared GB10
restoration/blending52.042s/peak5.614GB, excludes RAW decode/TIFF encode;10s unmet.

Public report docs/raw-kernel-phase-joint-v67-first2k-review.md, machine receipt
SHA2567fd672fc87f5fee695638ee37d6bb636fd5e1ff55984af562a99a00cc1b35e5c.
All26 image hashes,48comparison count, decision/remaining budget, JSON/local links
and whitespace checks pass. Model code unchanged; no full suite rerun claimed.
README keeps V43 representative crops and links current review. No promotion.

Next complete remaining8000 original updates only after verified isolated resume.
IMPORTANT: preserve original2k run/log/source and review byte-for-byte. Existing
artifact/publication hashes refer to that original metrics.jsonl, so appending
there would invalidate historical evidence. Use a separate continuation run path,
copy/freeze the existing log prefix, and restore model (not just EMA), EMA, all92
Adam states, best and Python/Torch/CUDA RNG from this exact2k checkpoint. Keep
model/data/seed50/B16/native256/BF16/LR1e-4/warm100/original10000 schedule exact;
only output destination/notes may change. Resume logs add the first resumed step
2001 even though log_every25; the full audit must explicitly validate that row
and original log prefix, not silently discard it. Verify this resume protocol
before launch, then full final development/analytic/hue/native/GFX/artifact review.
The continuation is not yet launched; the2k decision supports finishing the
planned optimization budget before treating the current deficit as convergence.
