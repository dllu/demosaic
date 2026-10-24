# Compare the released RawNIND pre-upsample variant on current quality panels

Recorded: 2026-10-23T19:04:30-07:00 (America/Los_Angeles).

Classified the previous goal turn as progress: the fixed low-frequency
correction was rejected from actual scores/native views. Revalidated the
V111 controller/child and all three waiting evaluation/material/export queues;
the fixed training is healthy. Continued with a stronger released comparator
while that trial trains, without adding GPU work or changing its recipes.

A current primary-release check confirms darktable's canonical Bayer RawNIND
uses the exact half-resolution checkpoint already retained here. Its package
also identifies the authors' pre-upsampled variant, which was not in our prior
comparisons. Retrieved that file through the Google Drive connector, then
verified its exact ID through the author README's model folder hierarchy and
read the publisher's training arguments. The original author source remains
at e80fb7b14dc440bba38c01f312fd3cc02deb566c. The args confirm four inputs,
funit32, preupsample=true, no transfer function and match_gain=output.

The new separately cached iter4320000 checkpoint is 31,057,675 bytes, SHA256
`3d8d5fab966f790f4adbaf1786ca1ee81cb027d9cd45220787247b0af99fd814`.
This is an observed byte pin, not a claim that the author published a separate
SHA256. All 46 tensors strictly load into the original UtNet2, 7,760,451
parameters, with no fallback/random weights. Source remains separately GPL-3.0
and the author offers weights under GPL-3.0/CC BY 4.0. Original half weights,
iteration4350000/SHA c1f7de3d…, retain their bytes.

Both use the same signed input, publisher global-ADC normalization and
input-only CFA-channel least-squares gain contract. The new network upsamples
the packed planes before its CNN, while half upsamples at the output head.
Different weights and training histories prevent attributing the whole gain
to that architectural difference. Four-CFA native64 controls have identical
canonical network inputs, inverse-flip errors at most 1.7882e-7 and exact
repeat predictions. Inputs, state, parameter IDs and per-forward RNG remain
unchanged in the actual quality calls. No CUDA is initialized.

First scored the same 12 cached material observations and original four
adverse-camera crops, and restored all six standing GFX 512 contexts. V104/V102
float predictions are reused rather than rerun. Pre-upsampled improves every
material case over half, but remains below V104 in every case:

| Four-source condition mean | V104 | RawNIND half | RawNIND pre-upsampled |
| --- | ---: | ---: | ---: |
| ADC-only | 39.49290 | 27.60011 | 28.13487 |
| ISO100 prior | 40.80494 | 27.59567 | 28.12808 |
| ISO12800 prior | 33.49300 | 27.11000 | 27.59760 |

Then completed both references on the full original camera development panels,
72 known and 90 unseen crops. Used frozen copied source, native B1/IEEE FP32,
two CPU threads/low priority. The older known metadata lacks global ADC white;
reused the exact recorded ADC/scales from the prior summary rather than
decoding original RAWs or guessing sensor levels. Every old half control
matches the prior CUDA primary scores within .0000496 dB. New numerics and
float outputs are committed to complete receipts before review rendering.

| Method | Known4 CFA PSNR | Unseen5 CFA PSNR |
| --- | ---: | ---: |
| V102 | 54.23709 | 53.97177 |
| V104 | 54.26606 | 53.91700 |
| RawNIND half | 54.08474 | 53.76822 |
| RawNIND pre-upsampled | 54.26068 | 53.86528 |

Pre-upsampled gains +.17594 dB on known scenes, 95% scene interval
[+.11324,+.23672], all four improving. Unseen gains +.09707, interval
[+.00655,+.17382], four of five improving; top_of_Expedit falls .07039.
V104 minus this stronger alternative is only +.00539/+.05172 dB, with wide
intervals spanning zero and 2/4, 3/5 scene wins. These are fixed development
sources; external training overlap remains unproven and the protected 16-scene
reserve remains unscored. The broad real-camera objective is still open.

Independent NumPy64 arithmetic rebuilds all 376 primary row records across
pilot/full runs, including overlapping pilot observations. Full-panel primary
PSNR discrepancy is at most 4.265e-6 dB. All 1,104 channel-gain normal equations
check against noisy observations, maximum independent refit error below
2.64e-7. Scene/pair/crop aggregation and 10,000 source bootstrap draws, seed 42,
are explicit; they do not quantify training-seed uncertainty. All 96 panels
across 32 triplets re-render exactly, and all 52 board cells were actually
viewed natively.

Pre-upsampled bark/fur is modestly clearer than half, still much softer than
V104. Both RawNIND variants smooth the specifically selected Canon dark fields
and score better than V104 there. GFX mesh/building edges remain more regular
with V104; the alternative improves some coarse sign/rail structure over half,
while foliage remains soft. Shared +2EV clipping limits saturated-light views.
GFX uses cached DSCF3879/3880, 512 contexts and native 160 crops, no new full-frame
output; ISO100 f/5.6 remains a separate qualitative reference, not GT. Camera
AHD is auxiliary, not exact RGB GT. No new V104 inference, training, RAW decode
or source-HDD access occurred; 378 reference-network forwards include controls.

Published two exact synthetic-GT triplets and the complete native boards in
the [current reference guide](../docs/rawnind-variants.md), with source/ROI,
checkpoint/noise/display and license records. Updated README, GFX, camera,
material, current-model and requirements guidance without changing historical
scores or the V104 selector. Preserve the stronger tested reference in future
quality comparisons. The publisher's wider funit48 alternative was identified
in the same model folder and its args read, but its weights/results remain
untested here. This comparison is not exhaustive or a SOTA claim.
[Complete executions, independent audits and native evidence](../docs/results/rawnind-preupsample-current-v1.json).
