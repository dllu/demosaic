# Queue complete GFX RGB16 comparisons

Recorded: 2026-10-22T11:54:24-07:00 (America/Los_Angeles).

The previous goal turn made progress by reviewing 110 further source candidates,
preparing six additional visual exclusions in a separate cohort, and verifying
its companion ROI catalogue. Revalidated the original V100 controller/worker
and waiting evaluation controller; their frozen inputs remain unchanged.

Added a source-frozen full-frame GFX queue after the seven-panel quality review.
It will restore all 101.996MP of cached DSCF3879 with V84, both final10k
continuations and RawNIND:CFA-channel. Shared settings are IEEE FP32,
tile512/overlap64/B4, +2EV, the original four native ROIs and two fixed neon/
platform ROIs. DSCF3880 remains an independent qualitative reference, not GT.
Each method exports linear-camera RGB16, tagged/ICC sRGB16, an overview and
native triplets. Private complete renders stay outside Git. Full-frame quality
and timing are pending; this does not gate the current V84 recommendation.

The queue uses the evaluation's already frozen numerical source. It waits for
the exact preceding controller to complete and exit, then starts its owned
worker under the existing RAM/disk resource policy. Failures remain preserved
without automatic retries. Production controller PID984425/create1792695189.65
is live and waiting. Plan:
`.cache/current-quality-20261022-v1/fullframe-v1/plan.json`, SHA256
`8a9cb830562db1e30ee618f69c839108ce3fbffb5403caa57c71c275d9868f77`.
Output namespace:
`/mnt/external/demosaic/v84-quality-fullframe-20261022-v1/`.

An actual cropped CPU512/one-tile smoke restored the cached foliage context
with V84 and RawNIND, then exported and decoded all four TIFFs. Verified 16-bit
RGB shape/type, color metadata and sRGB ICC tags; checked 33 full-width rows per
file against supplied float pixels, totaling 202,752 channel values. Largest
sampled quantization error is .501160DN16. This samples the encoder output;
it is not a whole-image precision comparison or a complete-camera run.
Both native160 triplets and both RGB16-derived overview PNGs were actually
viewed at original resolution. The underlying cropped-source shape is512×512,
not101.996MP, and CUDA is never initialized by this smoke.

The overviews also show isolated blue points outside the central160 crop in
both methods. These need input/reference/neighborhood inspection in the later
real-scene review before attributing a cause or fitting a correction.

All 36 focused ownership/IO/export tests pass, including rotated exports and
rejection of RGB8, missing ICC tags and changed decoded values. Ruff and
format checks pass. [Readiness evidence](../docs/results/v84-quality-fullframe-readiness-v1.json)
binds the smoke and live queue; current GFX/training docs record what is queued
and what is actually measured. No new model performance, speedup or SOTA claim.
