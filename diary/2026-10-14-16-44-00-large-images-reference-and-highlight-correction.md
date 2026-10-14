# Large images, reference comparison, highlight correction

The 1024-source cache completed: 925 train, 61 validation, 38 untouched test.
An immutable `commons-1024.jsonl` snapshot preserves the exact dataset while
four bounded preparation workers expand the main cache to 8192 sources. New
ingestion tests verify deterministic output across worker counts, unchanged
source DB bytes, cache recipe checks, license filtering and an OS writer lock.

Optimized inference with channels-last weights and packing only active tile
batches on CUDA. An actual warmed 100 MP run completed in 9.878 seconds, including
host setup/blending but excluding decode/encode, with 0.722 GB CUDA allocation.
A cold real GFX100S 102 MP run completed with valid 16-bit outputs in 17.043 s
for restoration. Corrected LibRaw's XYZ-to-camera matrix direction and added
neutral/matrix direction regression tests. Full processing latency is now timed
by the CLI; the older real run did not capture it.

Acquired the original RawNIND UtNet2 Bayer checkpoint from the authors' public
Drive link, plus GPL source/license, in external generated storage. No unsafe
pickle globals; weights load with weights_only=True. Recorded exact source and
weight SHA-256 and added a pinned reproducible download script. An optional
adapter preserves CFA geometry and compares both published input-mean gain and
observed-CFA least-squares gain. On the fixed 61-crop synthetic validation,
ours 32.381 dB rendered versus 28.914 for the stronger RawNIND gain mode.
This result is not sufficient to claim the requested real-world quality.

Visual review found pink saturated regions in the real RAW output. The original
clean target clipped independent sensor channels, which can encode that same
false color after conversion. Saved/stopped only our base-v1 process after its
step-500 checkpoint. A second experiment uses a reference-white target and
explicit WB/matrix conditioning while retaining physical input clipping.
Further changes add rendered highlight masking, ADC black offsets and source
snapshots for future runs. All are documented separately to avoid confusing
software capability with learned quality. All 27 tests pass after these changes.
At v2 step 3000, the neutral highlight diagnostic reduced chroma MAE from
0.015744 to 0.005378 (~66%), with rendered PSNR 34.646→34.943 dB. Inspection of
the scientific comparison confirms that the magenta center is reduced; thin-line
color errors remain. This does not establish real highlight quality.

Official DINOv3 approval is still pending. Its original license is included with
attribution; no weights have been obtained or used. Active jobs and experiment
details are in generated run/config/metric files; confirm process handles before
making scheduling decisions. Next work: inspect learned highlight behavior,
finish broad data preparation, train v3 on a larger immutable snapshot, and
extend comparisons across noise/CFA/exposure and real-camera crops.
