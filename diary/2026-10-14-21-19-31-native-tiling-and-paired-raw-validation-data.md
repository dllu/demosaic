# Native tiling, camera matrices, and paired RAW validation data

Previous goal turn was concrete progress: official DINOv3 full-corpus training,
427-photo validation, precision options and 52 passing tests were pushed as
8ee5d2c. This turn revalidated the clean tree and exact live training PID1825573,
then continued the full PROMPT.md objective. No agents were spawned.

## Actual tile-driver quality

Added scripts/compare_tiling.py. All 29 full-corpus validation images with native
512-pixel support are used without resizing; none support 768/1024 pixels after
8x8 binning. Three known 1024-pixel procedural scenes add larger blend/context
checks: constant .01, chirp and a clipped HDR disc. All four CFAs and seven
conditions share observations; border16 and a common eight-pixel overlap-strip
mask are explicit. Single-tile predictions are not ground truth. Summarization
now skips comparisons without shared source IDs, with a coverage regression test.

At frozen V6 step20000, photo 512/64 tiling is 33.37296 dB/0.930681 versus
256/64 at 33.34511/0.930500; paired PSNR gain .02785 dB, 95% source-bootstrap
CI [.01681,.03866]. SSIM's small difference has an interval crossing zero.
Shared-strip RGB MAE .012703 vs .012734 is similar. RawNIND is
28.72106/0.807805; the variance prior alone is 31.48027/0.905087.
The three large procedural sources favor 256-pixel PSNR by .18675 dB;
RawNIND has higher procedural SSIM, driven partly by the noisy flat. These
results support 512-pixel photographic serving without proving universal seam
absence. Receipts: docs/results/prior20k-tiling.json and full local artifact
/mnt/external/demosaic/evaluation/tiling-v6-step20k-full/.

A DINO-preview-only cap256 was then evaluated on exactly the same full suite.
Photographic 512-pixel output falls to 33.24654/0.926918, a .12642 dB deficit
(native advantage CI [.10127,.14854]); large procedural output falls to
45.58320/0.965719. The entire 256-pixel tile control has exactly zero metric
difference. Reject this cap for the quality path. No public/default model change
was made. See docs/results/prior20k-context-cap.json and the external source
wrapper in /mnt/external/demosaic/evaluation/tiling-v6-step20k-cap256/.

## Camera matrices and speed experiments

Repeated the 16-scene seven-condition diagnostic using actual WB/matrix examples
and recorded CFA from GFX100S, GFX50R, Q2 and a7R II metadata. V6 FP16 exceeds
V4 and RawNIND in overall means for each. V6 rendered PSNR/SSIM: GFX100S
31.2769/.918165; GFX50R 30.2702/.904331; Q2 31.3075/.919822;
a7R II 29.7549/.890092. These are the same 16 scenes under four metadata sets,
not 64 independent scenes or real-noise scores. No private source filenames are
in the numeric receipt: docs/results/prior20k-camera-matrices.json.

Inference prototypes keep physical FP32 but cast only 44 neural residual scales/
fusion gates to FP16, or compile with fixed global IEEE and precision-cast
emulation. The 16-photo RGGB FP16 pilot is nearly unchanged: eager31.895961,
compiled FP32 residuals31.895949, compiled FP16 residuals31.895857 dB. Full
quality validation would still be required before promotion. Prototype source
and original weight SHA are archived beside external result.json files.

For actual warmed 100 MP timing, only our verified training process was briefly
SIGSTOPped after checking UID, cwd, command, and a finite step40000 checkpoint.
A separate 180-second watchdog and finally block resumed the exact PID/state;
no restart/RNG reset occurred. Pause was 104.775 s, and training subsequently
advanced beyond step50000. Other processes were untouched. Warmed second runs:
eagerFP16 21.341 s, compiled FP32 residual features14.362 s, compiled FP16
residual features13.197 s. All produce finite full-size outputs. These runs use
WB/matrix metadata and fixed global IEEE, unlike the earlier BF16 benchmark;
do not attribute their difference to dtype alone. Resident graph/candidate
allocations also complicate peak CUDA memory interpretation. The 10s target is
unmet. Compiler/feature-cast prototypes remain unpromoted, and full DINO context
remains the quality path. Receipt: docs/results/prior20k-fp16-compile-timing.json.

## Real paired RAW sources

Primary-source follow-up inspected the RawNIND paper, official repository and
Dataverse catalog. Release1.0 is CC-BY-SA-4.0, with individual CC0 grants/credits
in permissions.txt. Added demosaic.paired and scripts/fetch_paired_raw.py:
metadata-only deterministic selection, strict publisher test separation,
bounded downloads, byte-count/MD5/SHA1 checks, SHA256 receipts, existing-file
preservation, and cleanup of only owned temporary files. The published descriptor
also lists XMP sidecars as clean images; those are excluded and regression-tested.
The older small test_reserve.yaml is not the current reserve; dataset.yaml flags
and corrected TEST filename prefixes govern selection.

Downloaded and verified 4 development scenes / 13 RAWs /365860063 bytes, and
all16 reserved Bayer test scenes /57 RAWs /2090382639 bytes. Test includes six
unknown-sensor scenes. Development scenes are 2pilesofplates,7D-1,
MuseeL-CopteArch-C500D,D60-2. RawNIND may have trained on these development scenes;
this is a disclosed comparator bias, not an independent test claim. Official
test images remain unused for model selection or inference. Sources and manifests:
/mnt/external/demosaic/references/rawnind-dataset/.
Numeric receipt: docs/results/paired-raw-acquisition.json. No paired sources were
added to Commons training. No personal images were modified or published.

A real Sony development reference probe shows LibRaw AHD, output_color=raw,
unitWB, gamma1, no auto brightness, maximum-adjust threshold0, user_flip0 still
has RGB scale about1/1.069 relative to our per-channel-white-level RAW units.
CFA-derived correction factors are R1.069106, G1.068986, B1.069041; residual
CFA MAE is about5e-6. This prevents a silent6.9% target normalization error.
Reference RGB must be calibrated against its own clean sensor measurements.
Preparation/alignment and paired quality scoring are not implemented yet.

Next concrete quality work: align each development clean/noisy pair independently
of model predictions, estimate a shared exposure gain, and report fixed valid
regions. Integer shifts require updating reference CFA phase; a measured-sample
camera metric can sample predicted RGB at the shifted clean CFA rather than use
a demosaicer as ground truth. AHD-derived rendered metrics can supplement it
once target units are calibrated. Noise conditioning must use noisy input only,
with disclosed estimator reliability/fallback. Hold official test and 2255 Commons
test sources until final model selection; do not tune against their targets.

## Training and remaining gates

V6 remains the exact live original process, training toward100000 steps. At
step50000 the balanced monitor is32.35511 dB/.931148. A finite midpoint review
was frozen at step51000, SHA2560827497572fdbbb3f84773ce02ea1247eae182a0f89700e9b72cd98568392afa,
under /mnt/external/demosaic/evaluation/prior-v6-half-review/. Its 16-photo +
16-procedural comparison and flat-response probe completed (session65332 exit0).
V6step51000 is32.39247/.932055 on the 16 photos and30.63590/.918910 on
the16 stress sources, versus V6step20000 at31.88176/.925267 and29.91722/.901137,
and V4step30000 at31.35189/.916532 and30.58540/.917495. The earlier average
stress deficit has closed; individual cases still vary. At scene level.01,
retained sigma fractions improve20k->51k: ISO1600 .23974->.20088,
ISO12800 .21782->.18488, shadows .26804->.20392. These remain above RawNIND's
flat suppression. Keep the current recipe training; do not infer a need for a
new architecture from the earlier20k failure without reviewing convergence.
Receipt: docs/results/prior51k-midpoint.json. The photo score uses16 scenes,
not the entire427-photo suite.
Main PID1825573 remains active. Active original run predates the lineage fix;
merge its verified initialization.json receipt into any final export if needed.

All59 tests pass, including integrity/split/sidecar/network-failure cleanup and
partial-evaluation coverage cases; Ruff check/format passes. Full convergence,
paired real-RAW preparation/evaluation, final broader validation/test, final
RAW quality and idle final-model speed remain. The full PROMPT.md goal is active.
