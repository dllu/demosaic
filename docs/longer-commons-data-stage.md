# Longer matched Commons-data comparison

V63 and V64 have completed their first4,000-update review. The
[performance report](long-commons-v63-v64-first4k-review.md) finds a small mixed
data effect and no clear native detail gain. Neither is promoted or automatically
continued; whole states and original20,000 schedules remain frozen. This tests
more scene diversity with a longer training
schedule after [V61](sensor-mean-v61-first1k-review.md) and
[V62](sensor-mean-v62-first1k-review.md) failed to improve the overall color/detail
tradeoff. V43 remains the working
reference, with the standing real-camera tests and protected-final boundary intact.

The preparation/launch/queue notes below retain the original workflow history.
All primary, statistics/hue and artifact stages have now completed and their
owners exited. The completed report supersedes their historical pending-status
statements and records the actual quality decision.

[Actual launch, frozen plans/configs/source, production startup and CUDA checks](results/long-commons-v63-v64-first4k-launch.json).
[Control recipe](../configs/dino-convnext-wide-long-control-b16-v63.yaml).
[Expanded recipe](../configs/dino-convnext-wide-long-expanded-b16-v64.yaml).

| Setting | V63 control | V64 expanded |
| --- | --- | --- |
| Commons training sources | 40,170 | 66,934 |
| Commons cache | Original complete 4× | Reviewed complete extended 4× |
| First review / original planned updates | 4,000 / 20,000 | 4,000 / 20,000 |
| Other settings | Shared | Shared |

Both start from completed V60 wide-palette step4000 **EMA**, SHA256
`1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e`,
with fresh AdamW/EMA, seed 49, LR 1e-5, warmup 200, batch 16/native 256 and BF16.
This is a deliberate new stage; the original V60/V62 runs and schedules remain
immutable. Parent comparisons include additional updates and an optimizer reset;
only the two new matched arms isolate training-data membership.

The 32,904,704 restoration parameters train; the pinned DINOv3 backbone remains
frozen. Both retain the 8-stop palette, loss weight 0, 128 native captures from
106 scenes, original 32 paired scenes, all source fractions and noise/ADC,
4×→geometry/PSF→area2, worker counts and original 8× validation. The expanded
manifest SHA256 is
`7ed635903e4dd698081475a3667c8a14bb3b9f5f628a0917a5e336406faaecde`.
Its full 4×/8× cache and membership checks are in the
[completed corpus review](commons-incoming-v3.md). The new 75,806-source v4 corpus
has completed its [separate integrity and content review](commons-incoming-v4.md);
neither arm substitutes that larger corpus.

The actual parent/source/data CUDA fixture executes seven discarded updates per
arm using production seed 49, batch 16/native 256/BF16 and the 20,000-step
schedule. It covers Commons, native and paired domains. All 91 model/91 EMA
tensors and 89 AdamW states are finite. Two portable EMA photo predictions match
reconstruction from the raw saved state exactly. Both fixtures share domain
choices/LRs and all native/paired input hashes; real Commons batches differ as
expected. Peak CUDA allocation is 7.200 GB, not a production throughput result.

Fixtures disable data workers, force real Commons photographs instead of smooth/
procedural examples, and use two validation images to check the changed data
path. Production retains its original fractions, workers and validation. No
training/optimizer/EMA implementation changes were made; the same frozen source
already has CPU restart checks. These fixtures do not establish convergence,
quality, deterministic CUDA optimization after restart or a new CPU restart result.

The controller verifies preceding owner exits and the completed V62 review,
source/config/data guards and successful fixture before launching. It runs each
arm only to 4,000 under its original 20,000 schedule, freezes complete model/EMA/
AdamW/RNG state, and checks all 161 logged domain/LR choices and unchanged-domain
input hashes. Commons hashes may differ because membership differs. Further
updates require a complete native/photo/paired/hue/GFX review and preserve whole
state and the original schedule; there is no automatic continuation or promotion.

Controller PID 1988162, creation 1792207826.66. Status:
`/mnt/external/demosaic/runs/long-commons-v63-v64-first4k-workflow-v1.json`.
Plan and archived controller/configs:
`/mnt/external/demosaic/benchmarks/long-commons-v63-v64-first4k-workflow-v1/`.
Log: `.cache/train-long-commons-v63-v64-first4k-v1.log`.
Inspect actual PID/creation and child status before acting; do not start duplicates.

The [primary-panel review is queued](results/long-commons-v63-v64-first4k-review-queue.json)
behind that exact controller's exit. Owner PID 2036802, creation 1792209597.41,
uses the immutable panel operators and old model worktree. It evaluates both
new 4,000-step models: 62,020 photo/procedural/classical rows, known360/unseen450,
1,344 analytic rows, eight full-frame GFX crop triplets, twelve other-camera
triplets and 64 selected CPU-color predictions. Historical V60/reference bulk
neural panels are retained. Independent statistics/state/hue/native review and
a quality decision remain required after primary evaluation; nothing is promoted
or continued automatically.

V63's frozen step4000 checkpoint is
`/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step4000.pt`,
SHA256 `5f29bd7efb94b72491cff22575c0565995326644823bcb802444214c8f2c6bd6`.
This is a training boundary, with the original 20,000-update schedule preserved;
it is not a quality result or a model promotion.
V64's corresponding frozen checkpoint is
`/mnt/external/demosaic/models/dino-convnext-wide-long-expanded-b16-v64-step4000.pt`,
SHA256 `c0a00177b676caddea39b225f2fba1bcdc0b57d6fd543500363c8c908d83df81`.
The [independent two-arm boundary check](results/long-commons-v63-v64-first4k-trained-boundary.json)
verifies both whole states, original recipes/source/data/RNG and all 161 matched
domain/LR choices. All logged native/paired input hashes match; 79 logged Commons/
procedural-domain batches differ as allowed by the data experiment. Both original
20,000-update schedules are preserved. Paired panels have completed and the full
427-photo panel is running; these are not complete quality-review results.
An [independent CPU state check](results/long-commons-v63-first4k-state-check.json)
verifies the full checkpoint hash, finite 91 model/91 EMA tensors and 89 AdamW
states, all optimizer steps at 4000, complete RNG, archived model source, all four
manifest hashes and the 161 frozen training-log rows. That earlier receipt
covers V63 only and reports no restoration-quality result.

The [statistics and hue follow-up is also queued](results/long-commons-v63-v64-first4k-statistics-hue-queue.json),
controller PID 2055575, creation 1792210364.08. It waits for actual primary-owner
2036802 to exit. Its frozen operators audit the five-method primary panels and
produce 84 comparisons: V64 minus V63, plus each arm against retained V60 full4k,
V58 and V43 scores. Observation metadata, coverage and nullable support must
match. Historical classical drift is fully recorded under the existing four-F32-
ULP bound. Source bootstrap intervals do not measure training/selection uncertainty.

The hue stage uses the original 1,176 observations for V60, V63, V64 and the
released RAW reference. It reuses 2,352 audited parent/reference arrays and runs
only 2,352 new predictions. Independent Torch64 checks cover all 4,704 arrays/
28,224 metric fields; a separate arithmetic audit checks 72 groups/864 descriptive
scalars. Twelve native grid triplets remain subject to visual review. Whole-state
and primary-native artifact review is still required afterward; this queue cannot
promote or continue a model.

[Executed CPU operator checks](results/long-commons-review-tools-CPU-preflight.json):
the new score tool audited 87,962 genuine historical cases and reproduced 84
published, reversed or self comparisons, maximum scalar/interval error 3.13e-17.
This replay used seven historical methods, while the new panel expects five.
The grid wrapper reused 2,352 actual audited arrays without inference and rendered
six PNGs with exactly matching pixels/hashes and display metadata. Both reject the
actual pending primary workflow before writing an apparent result. The first grid
attempt incorrectly treated the released-reference directory as a file; corrected
checkpoint/export/receipt verification passes, and the failed log/source remain.
These are engineering checks on old outputs, not new V63/V64 quality evidence.

The [remaining state/native/RGB16 audit is queued](results/long-commons-v63-v64-first4k-artifact-queue.json)
after actual statistics/hue owner 2055575 exits. Controller PID 2060575,
creation 1792211119.29, runs only the tested CPU artifact checker. It checks both
whole states against every original recipe field (with the resolved validation
protocol checked by hash), complete RNG/source/data and all 161 matched logs.
Then it verifies 38 native triplets, 26 saved float arrays and four full RGB16
files. Noisy/reference pixels and transform metadata must match retained V60
exactly. Both models must include two distinct exact-target photographic crops
and all sky/building/foliage/fence GFX regions, with real references labeled non-GT.

The checker also ties each of the eight GFX denoised PNG panels to the identical
native ROI in its full sRGB16 TIFF, requiring exact 8-bit codes. Three-camera
panels are independently rerendered from saved F32 data, WB/matrix/exposure and
native coordinates. CPU/GPU FP32 rounding can differ at an 8-bit boundary; a
preview-only bound of at most one code in at most 16 channel values per 160×160
panel is defined from historical artifacts before V63/V64 output review. Every
difference is recorded. This does not relax source/reference pixel equality or
any restoration-score/color check.

[Executed CPU preflight](results/long-commons-artifact-CPU-preflight.json) verifies
the actual completed V63 state and replays genuine historical artifacts for the
two older arms, explicitly selecting the relevant methods from that larger
report. All 38 PNGs/26 F32 arrays/four RGB16 files match the existing complete
audit; all eight full-TIFF crop comparisons are exact. Across 36 three-camera
rerenders, six channel values differ by one code, at most one per panel. The
first test driver used relative instead of absolute paths in its final historical
file lookup; the corrected driver passes with the artifact checker unchanged.
Both attempts and source hashes are retained. The actual pending primary workflow
is rejected before output. No GPU, inference or RAW decoding occurs in this check.
Actual visual inspection, statistical interpretation and the quality decision
remain required after the queued integrity work; no model is promoted or continued.

Reports must include at least two native noisy/denoised/exact-GT photographic
triplets and DSCF3879/3880 sky/building/foliage/fence crops, with accurate non-GT
labels for independent real references. No protected-final model score is used.
The desired real-photo quality, SOTA and 100 MP within 10 seconds remain unresolved.
