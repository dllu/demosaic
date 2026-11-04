# V155 matched cleaner-parent audit

Recorded: 2026-11-03T19:51:59-08:00 (America/Los_Angeles).

V154's weak-error reweighting improves standalone flats but worsens quiet
neighbors and natural detail. A late band-limited head cannot directly repair
the parent's coarse/DC errors. Before another head trial, compare V120 and
V143 on exactly the current822 cached RAW inputs. V120's prior coarse-flat
advantage is a hypothesis on this support, not a presumed broad quality gain.

The first exact-replay assumption failed on the first old mesh array: maximum
difference0.0017089583 DN16. One actual V143 root/DINO call occurred; no V120,
training or new noise ran. The old collector used cuDNN benchmarkTrue while
this replay used deterministic algorithms and benchmarkFalse. This settings
difference may explain the arithmetic mismatch; it has not been isolated as
the sole cause. Do not erase the failed check or silently adopt old controls.

The corrected v2 design evaluates both parents afresh under identical
deterministic FP32/channels-last/no AMP/no TF32 settings. This avoids attributing
cross-policy differences to parent quality. Each parent gets all822 observations
and actual root/DINO hooks,822 each/1644 total, with per-case physical noise.
Archive V143's full outputs locally and V120's externally,2.211GiB per model.
Launch/storage guards keep52GiB available RAM,12GiB CUDA allocation quota and
96/208GiB local/external runtime reserves. Models and official DINO hashes are
fixed; states/inputs/RNG and frozen code are audited. Targets/reference do not
enter forward. No source/RAW/original lookup, noise redraw or dataz access.

The failed root and its plan/claim/trace/status/log/source bytes remain under
V155-parent-comparison-v1. Its runner subsequently received only formatting
before the substantive v2 design change; v1 source was preserved before either.
The v2 frozen runner and86 neural files are immutable in the new root.
No training is authorized by this diagnostic controller and none is started.
Both standing real scenes/windows/priors/JPEGs remain in fixed qualitative
review, not scored against exact GT. All protected captures/siblings remain
excluded from training and original files read-only.

CPU-only paired scorer and separate NumPy64/Decimal auditor are prepared in
reporters-v1. Their change/added-error fields mean differences from newly
evaluated V143, not a trained correction. New parent results and actual native
viewing remain pending. The fine-detail/clean-sky objective remains active.

Preparation recorded: 2026-11-03T19:56:20-08:00 (America/Los_Angeles).

Final review completed: 2026-11-03T20:15:28-08:00 (America/Los_Angeles).

Both fixed parent collections completed once:822 V143 and822 V120 root/DINO
calls under the same policy, with model/backbone/input/RNG checks. V143 took
293.89s and V120254.62s inside their measured loops, each peaking1.805GiB CUDA.
These timings exclude model loading and are not full-frame speed claims.

The cleaner-parent hypothesis has mixed results. V120 native512 block32
noisy-flat RMS improves1.59% at ISO6400 and2.36% at ISO12800, while total RMS
worsens5.11/2.31% and spatial RMS5.15/2.54%. Both retain broad native mottle.
V120 mesh response rises5.05% but reaches only2.31% of GT, with present full
and actual blank errors worse. Faint natural-band response falls2.99–5.68%.
No convincing new real cab crossings appear under either prior/window.

Quiet-mask RMS improves0.91/0.39%, but ISO6400 quiet spatial RMS worsens0.46%;
ISO12800 spatial RMS improves1.08%. Whole metrics and DC changes do not imply
uniform quiet safety. V120 ADC-photo RMS improves0.60%, still less than V150's
roughly3.06% gain. ADC sloped full/spatial/block32 errors worsen33.26/25.08/112.65%,
with crop-block32 and worst DC also worse. Constant ADC full RMS rises4.09–5.12%.
Do not promote V120 as a universally cleaner noisy/affine parent from this result.
V120 remains the general recommendation on broader427-photo/camera/frame evidence;
V143 remains the matched noisy-detail control, with parent strengths explicit.

The fresh V143 complete model-state hash matches the retained original model.
All56 newer deterministic control arrays are bit-exact;766 older quality arrays
differ slightly, overall maximum0.09374857 DN16. The known cuDNN policy difference
may explain this but was not isolated as sole cause. Paired scores exclusively
use the new arrays, avoiding an across-policy comparison.

Two CPU reporting failures are preserved in addition to the first exact-replay
assumption. CPUv1 missed train_v43_quality_trial.live required by a dynamic
photo-metric import. CPUv2 then reached an old6330/4932 row-count assertion.
CPUv3 adds the exact helper and corrects the expected1644/1644 count only;
metric arithmetic is unchanged. No GPU/parent/training replay occurred.
All13 recorded owners, including these failed controllers/workers, are terminal.

Independent NumPy64/Decimal audit passes14,036 scalars over1,644 rows, maximum
difference3.97904e-13, and180 Decimal reductions. All12 real rows remain unscored.
Actually viewed64 native figures in16 original-detail unscaled sheets after the
image-tool outputs arrived. Both parents have two noisy-flat triplets plus two
mesh, two natural and two ADC-photo triplets. All160px cells are unchanged;
19,046,400 RGB channels and repeat-cell equality are checked. Both standing
real scenes retain sky/building/foliage/coarse fence and fine cab mesh under
both priors/windows/JPEGs. ISO100/AHD/JPEG references remain qualitative,notGT.

Published32 receipts byte-exact, including all failed plan/status/log/trace/source
evidence,64 native PNGs/16 triplets and full provenance. README, current-model,
research, experiment and documentation indices now compare both strengths and
costs. Publication verifier checks86 neural hashes,all1644 output fingerprints,
8220 input fingerprints,80 rounded numeric cells and document links.
Actual total work is1645 parent calls and1645 nested DINO calls, including the
single failed replay;zero training/noise/RAW decode/original lookup. Both complete
2.211GiB archives remain in their local/external destinations,96/208GiB reserves
maintained;no evidence deleted/moved. All original personal media remains
read-only and protected scenes/siblings excluded. /mnt/dataz remains unused.

Next quality work should directly address spatial/coarse error control beside
weak-detail supervision. A late affine-removed band cannot remove parent DC/
out-of-band errors, and changing between the current parents alone does not fix
the real fence or quiet blobs. Retain previous V153 mesh response,V154 flat gains,
V150 ADC gains,and quieter V151/V152 controls as measured comparators.
No V156 implementation or training has started. The broader objective stays active.

[Full matched-parent report](../docs/matched-parent-comparison.md) ·
[Final evidence](../docs/results/v155-matched-parents-final-v1.json) ·
[Publication verification](../docs/results/v155-matched-parents-publication-verification-v1.json).
