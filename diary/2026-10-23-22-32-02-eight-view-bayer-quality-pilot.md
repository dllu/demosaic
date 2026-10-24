# Eight-view Bayer quality pilot alongside V111 diagnostics

Recorded: 2026-10-23T22:32:02-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress: it launched V111's full CPU
texture/color evaluation, queued a source-bound independent auditor and passed
actual parent-output and independent arithmetic checks. This turn verified all
seven exact live process handles before continuing. The original448 weak/flat
cases have now finished; all15 cells in the three-model native board were
actually viewed at100%. V111 remains close to V104 in the selected high-noise
carrier and flat views. Dark period8 structure is still largely missing;
period16 is visible but uneven/soft. Full independent grid audit waits for the
color worker's original1176 cases to finish.

A fixed eight-view V104 pilot now tests whether geometric averaging reduces
orientation-dependent reconstruction artifacts. It uses all20 original cached
inputs: four photographic sources at ADC-only/ISO100/ISO12800, the two original
V104-adverse Canon M100 fields and six standing GFX contexts. All inputs,
references, source/ROI choices and original V104 floats were pinned before
viewing any new pilot scores. This is a quality option requiring eight forwards,
not an architectural or speed improvement.

Full mosaics, spatial variances and2x2 CFA color tiles receive exact90-degree
rotations/reflections. WB/matrix and physical shot/read conditioning remain
fixed. Predictions return to the original coordinates and receive an equal
float64 mean before float32 storage and shared display conversion. There is no
interpolation, gain fit, target-dependent weighting or new noise draw.

The geometry checks pass exact sensor-sampling commutation and inverse equality
for four CFAs, non-square26x38 fields, signed below-black/above-white samples,
RGB reconstruction and mean reduction, with inputs and Torch RNG unchanged.
The first fixture's ramp stopped below1, so its intended above-white assertion
failed after all geometric equalities passed. That executed source and failure
remain preserved; changing only the fixture range makes the full check pass.
No neural inference occurred in either geometry check.

The live pilot runs CPU2/nice10/IEEE FP32 from the original final20k V104 EMA,
with160 declared model/encoder forwards. Every identity view is replayed against
its original saved V104 float. Every canonical per-view output and equal mean
is retained. A separately pinned queue will independently rebuild all20 means
and photo/camera PSNR/chroma/gradient scores, then render all40 native triplets
and80 distinct board cells. Actual viewing remains separate. AHD and ISO100
captures are explicitly approximate/independent references, not exact RGB GT.

Private execution and review roots:
`.cache/current-quality-20261023-v1/V104-dihedral-pilot-CPU-v1/`;
output `/mnt/external/demosaic/V104-dihedral-pilot-CPU-20261023-v1/`.
Original V112 training and all matched evaluation/export/material queues retain
their bytes and priorities; no production/default inference change was made.

Completed review recorded 2026-10-23T23:23:19.918549-07:00 (America/Los_Angeles).

The original160-forward pilot completed; all20 identity views exactly match
retained V104 outputs and NumPy64 rebuilds every equal mean bit-exactly. All80
native board cells were actually viewed. Four-source mean photo PSNR gains are
+.56814/+.29317/+.08187dB at ADC-only/ISO100/ISO12800; all12 cases improve.
The two original adverse camera fields gain+.31344/+.26734dB, still below the
stronger RawNIND pre-upsampled reference. Fine high-noise detail, real foliage
and broad colored dark-field blotches remain. GFX changes are small.

Production now has optional `--self-ensemble dihedral8` for infer, benchmark
and linear-DNG export. The default remains single view. Exact full-mosaic,
variance and CFA color transforms plus a streaming float64 camera-RGB sum keep
all pixels native and memory bounded by one view. Every output receipt records
the policy/views per tile; no weights or training changed.

Forty actual CPU production forwards reproduce four original pilot cases
bit-exactly and verify real native256 tiled RGB16 write/read. Sixteen successful
CPU/GB10 validation forwards agree within1.79e-7 camera units, with identical
rounded PSNR, on the fixed128 context. This small compatibility run overlaps
V112 and has no throughput claim. All32 focused geometry/tile/CLI/RGB16/DNG
checks pass, including hot-pixel and cluster export with both inference modes.

The original queued renderer failed its frozen-source output-location check.
A new version writes to external storage and succeeds, preserving original
source/queue/directory/status. The first GPU validator moved a previously used
CPU model without resetting device-specific noise tables; a separately pinned
v2 repeats identical conditioning after placement, matching production order.
Original failed source/plan/log and successful v2 evidence remain preserved.

A complete101.996MP V104 eight-view linear/sRGB RGB16 export is queued after
the exact original matched full-frame controller exits successfully. Its frozen
public source and cached DSCF3879 hash are pinned. No original CUDA training,
evaluation or export queue is interrupted or changed. Full photo/camera/color
qualification for eight views remains open; no SOTA or speed-target claim.

[Completed pilot, actual native crops, code/tests, CPU/GB10 verification and queued export](../docs/results/v104-dihedral8-pilot-v1.json).
