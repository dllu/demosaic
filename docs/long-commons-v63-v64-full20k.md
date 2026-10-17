# Finish the original matched Commons schedules

V63 and V64 are deliberately continuing from their reviewed4,000-update whole
states to the **original20,000 endpoint**. The first4k comparison improved photo
means over V60, but found a small mixed data effect and soft native detail.
The later completed V67 RAW-only reconstruction experiment loses primary quality
and weak detail. Return to the stronger RGB+DINO path and complete the original
longer-data comparison before drawing conclusions about its budget. This is a
research decision after both reviews, not automatic continuation or promotion.

[Actual launch, source/state/data guards, genuine CUDA resume fixtures and startup](results/long-commons-v63-v64-full20k-resume-launch.json).
[First4k quality review](long-commons-v63-v64-first4k-review.md).
[Completed negative RAW-head review](raw-kernel-phase-joint-v67-full10k-review.md).

| Setting | V63 control | V64 expanded |
| --- | --- | --- |
| Commons train membership | 40,170 | 66,934 |
| Whole-state resume | Step4,000 | Step4,000 |
| Remaining original updates | 16,000 | 16,000 |
| Original endpoint | 20,000 | 20,000 |
| Seed/LR/warmup | 49 /1e-5 /200 | Same |
| Batch/native patch/precision | 16 /256 /BF16 | Same |

[Control continuation recipe](../configs/dino-convnext-wide-long-control-full20k-b16-v63.yaml)
and [expanded continuation recipe](../configs/dino-convnext-wide-long-expanded-full20k-b16-v64.yaml)
change only output run and experiment notes. Source bundle remains
`c9058d90d7d77e61ad7ec53293b805d8ea72da173318e38d1329e138215544c8`.
The original4k runs/logs/checkpoints/source and performance review remain exact.
The new outputs retain the original log prefixes. No EMA reinitialization,
optimizer reset, schedule retiming or new training budget is introduced.

Original checkpoint SHA256:

- V63: `5f29bd7efb94b72491cff22575c0565995326644823bcb802444214c8f2c6bd6`.
- V64: `c0a00177b676caddea39b225f2fba1bcdc0b57d6fd543500363c8c908d83df81`.

Both retain frozen genuine DINOv3 ConvNeXt,32,904,704 trainable restoration
parameters/89 tensors,91 model/91 EMA tensors, native128/paired32, workers4+2+2,
fractions.25/.25, wide8 palette, original noise/ADC and4×→geometry/PSF→area2.
Four manifest hashes and the original8× validation/protocol stay fixed. The
new [85,048-source corpus](commons-incoming-v5.md) remains separate. Only the
declared Commons membership differs between arms; changing it mid-run would
invalidate that comparison.

## Executed restoration checks

Two discarded25-update CUDA fixtures use the genuine respective4k states and
full production B16/native256/BF16/workers/data recipe. Hooks on the real frozen
trainer verify original **model rather than EMA**, all89 AdamW states, initial
EMA, and Python/Torch/CUDA RNG before the first data fetch. Each reaches4025
with finite91/91/89, all optimizer steps4025, all89 model/EMA parameter tensors
changed and normalization buffers exact. Actual DINO hashes stay unchanged,
with no gradients. Best value and original V60 initialization lineage remain.

Independent CPU replay checks both actual4025 checkpoints, original recipes,
source rebuilt from archived bytes, all data/protocol hashes, complete RNG,
161-row prefixes and resumed4001/4025 rows. Every logged LR follows the original
20k schedule. Production V63's actual4001/4025 domain/LR/input hashes match its
discarded fixture. CUDA optimization is not claimed bitwise deterministic.
Fixture states are not production initializers.

The first fixture launcher invoked uv from the archive directory and failed to
import Torch before model/training. That log is preserved. Actual fixtures use
the existing locked repository interpreter and repository cache environment;
no model state or training run was restarted.

## Live execution and required final review

Controller PID3228279/creation1792233978.99 runs V63 first, child3228295/
1792233981.29 at launch. It then audits/freezes the original20k boundary before
starting V64. Status:
`/mnt/external/demosaic/runs/long-commons-v63-v64-full20k-workflow-v1.json`.
Plan, frozen package, fixtures, drivers and logs:
`/mnt/external/demosaic/benchmarks/long-commons-v63-v64-full20k-workflow-v1/`.
Check actual PID/creation/status before acting; an observation timeout is not a
training failure. No automatic retry is installed.

The final state gate checks91/91/89, complete RNG, source/data/recipe/lineage,
all802 training rows including161 original and641 resumed, first-resumed input
witnesses and the original LR schedule through1e-6. Both arms must share every
logged step/domain/LR and all unchanged native/paired hashes.

The control has now completed and passed this boundary gate. Its immutable20k
checkpoint hash is
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
The expanded arm then started as child169989/creation1792243965.62. An
[interim CPU native comparison against control4k](long-commons-v63-control-original20k-CPU-review.md)
executes eight fixed observations at both endpoints, with independent array
checks and sixteen actual native views. The fabric photograph regresses,
building improves slightly, and two selected colors improve; GFX detail stays
soft. This does not promote the control. Expanded20k and the full two-arm review
remain pending; these launch identities should be checked against live processes.

Primary-review owner PID3231021/creation1792234172.79 waits for the exact
training controller to finish and exit. Its status is
`/mnt/external/demosaic/runs/long-commons-v63-v64-full20k-review-workflow-v1.json`.
At capture it is live and child-free, with all seven panel outputs absent.
Calling its gate against the actual running controller rejects before output.
It will separately audit both20k states and evaluate only the two new models:
known360/unseen450/full42762,020 cases, analytic1,344 cases, two full GFX outputs
with eight native crops, twelve other-camera crops, and64 CPU-color predictions
with an independent audit. Immutable previously executed panel tools are reused.

The [final statistics/hue/artifact follower is now queued](results/long-commons-v63-v64-full20k-final-review-queue.json)
under PID3269508/creation1792234878.14. It waits for the exact live primary owner
to succeed and exit, with no child or output at launch. Status:
`/mnt/external/demosaic/runs/long-commons-v63-v64-full20k-final-review-workflow-v1.json`.
Calling its gate against that actual pending primary rejects before inference.
Its frozen operators and1,483 file guards are archived in the corresponding
benchmark directory. Verify actual PID/creation/status before acting.

The [final-review operator](../scripts/review_original_long_schedules.py) retains
the previously executed measurement and artifact kernels. It adds24 comparisons
against each arm's own4k checkpoint to the existing84 comparisons versus the
matched arm/V60/V58/V43:108 comparisons and27 classical witnesses over62,830
primary cases. It preserves1,000 paired source bootstrap draws/seed42, metadata/
observation identity and the original numerical bounds. Progress along an
original trajectory does not isolate architecture/seed effects or prove convergence.

CPU execution on the actual completed4k panels reproduces all84 published
comparisons and coverage/arithmetic exactly. Twenty-four self-progress
comparisons and their intervals are exactly zero. The actual pending20k owners
are rejected. The hue selector independently verifies all2,352 retained V60/
reference array hashes and correctly identifies the genuine4k arms as absent
from that baseline grid. No inference or fabricated20k data is used in these
checks. The future completed20k path remains unexecuted.

After primary completion, the follower measures only the2,352 new hue predictions
and separately reuses2,352 audited V60/reference arrays with unchanged source/
observations/precision. Independent checks rebuild28,224 fields and864 group
scalars. It then checks both original20k states and38 native PNGs/26 F32 arrays/
four full RGB16 files. Four supplementary CPU neon/platform predictions and
their independent audit follow. All56 new native views and an explicit quality
decision remain manual; none is replaced by an integrity receipt.

The isolated work directory now links its relative GFX and three-camera paths
to existing warm repository caches. Both RAF hashes and all three other camera
RAW hashes verify locally. No originals were recopied or read, and the frozen
selection/config/model source did not change.

Final actual native views and an explicit quality
decision remain required. Reports must include at least two unresized noisy/
denoised/exact-GT photo triplets per improved model and accurately labeled GFX
sky/building/foliage/fence references. The independent ISO100 exposure is not GT.
Protected-final model scores remain unused. V43 remains the working reference;
SOTA, broad real-photo superiority and the10-second target remain unmet/unproven.

The [completed Commons content audit](commons-content-overlap.md) freezes
additional418/416-source sensitivity subsets before either20k full427 panel
runs. After the original queued panels/statistics close, derive those additional
photo comparisons from their actual saved case logs and fixed source IDs.
Keep the original427 results, paired protocol, all56 native views and quality
decision. These are known-series/site sensitivities, not certified scene-clean
subsets. No queued operator, active membership or original schedule changes.
