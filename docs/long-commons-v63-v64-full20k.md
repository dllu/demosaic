# Original matched Commons schedules: completed review

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

V63 and V64 both completed their **original20,000-update schedules**. The actual
trainers and training controller exited; both audited immutable checkpoints
verify. The primary evaluation, statistics/hue/artifact work and all58 native views are
complete after a source-audit working-directory recovery. The
[full performance review](long-commons-v63-v64-original20k-review.md) finds a
small positive photo data effect, with persistent texture/color failures.
Neither endpoint is promoted; V43 was the reference for this experiment.

[Actual training completion, checkpoint hashes and logged cross-arm checks](results/long-commons-v63-v64-original20k-training-completion.json).
The continuation returned to the stronger RGB+DINO path after the negative V67
RAW-head review. Its first4k photo means improved over V60, but the data effect
was small and mixed and native detail stayed soft. Completing the original
schedule preserves that matched comparison without adding training budget.

[Actual launch, source/state/data guards, genuine CUDA resume fixtures and startup](results/long-commons-v63-v64-full20k-resume-launch.json).
[First4k quality review](long-commons-v63-v64-first4k-review.md).
[Completed negative RAW-head review](raw-kernel-phase-joint-v67-full10k-review.md).

| Setting | V63 control | V64 expanded |
| --- | --- | --- |
| Commons train membership | 40,170 | 66,934 |
| Whole-state resume | Step4,000 | Step4,000 |
| Resumed original updates | 16,000 | 16,000 |
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

## Completed execution and quality review

The training controller ran the control then expanded arm and exited after both
original20k boundary gates passed. The immutable checkpoint hashes are:

- V63: `ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
- V64: `69d08a3bacf8ea436d807512c7a5fd61cb7f119d1f869bd5eab555c2473efe6d`.

Each gate checks91/91/89, complete RNG, exact source/data/recipe/lineage,
normalization buffers,802 logged training rows and the original LR schedule.
Direct log checks reproduce all1,604 LRs exactly, all802 paired step/domain/LR
fields match, and all375 logged native/paired observation hashes match. Both
original4k checkpoints and their original report remain unchanged. This does
not claim separately hashed unlogged observations.

The [interim control CPU diagnosis](long-commons-v63-control-original20k-CPU-review.md)
remains preserved. The completed primary review subsequently evaluates known360,
unseen450, full42762,020 and analytic1,344 cases, two full GFX outputs,12 other
camera crops and64 selected CPU-color predictions with independent checks.
It used warm local RAW caches and the frozen producer package; no cold original
reads or active membership changes occurred.

The [final-review operator](../scripts/review_original_long_schedules.py) preserves
108 comparisons including24 own4k-progress comparisons,27 classical witnesses,
1,000 paired source-bootstrap draws/seed42, shared observations and the original
numerical bounds. Its hue stage performs2,352 new predictions and reuses2,352
verified V60/nonlocal arrays; independent checks rebuild28,224 case fields and
864 group scalars. The final state/artifact audit covers38 primary PNGs,26 F32
arrays and four RGB16 files. All1,483 frozen file guards still pass.

The final workflow stopped at the supplementary GFX source check because that
auditor resolved relative paths from the current checkout while the producer
ran in its frozen checkout. The original failed status and log are preserved.
Running the unchanged auditor from the producer directory verifies all37 source
hashes and four supplementary triplets, without inference, altered outputs or
relaxed bounds. The separate
[completed review receipt](results/long-commons-v63-v64-original20k-review.json)
records this recovery; it does not overwrite the original controller's failure.

Actual native views total58:38 primary +12 hue +4 supplementary +4 selected
CPU-color previews. This corrects earlier planning prose estimating56. The
[complete gallery](long-commons-v63-v64-original20k-native-gallery.md) preserves
all original pixels; the performance report includes two exact-target photo
triplets per endpoint and standing GFX foliage/fence crops. ISO100/AHD and
RawNIND references remain accurately labeled as qualitative, never exact GT.

The [completed content audit](commons-content-overlap.md) froze418/416-source
sensitivities before the20k panels. Their
[actual application](results/commons-source-sensitivity-original20k-v1.json)
reproduces27 full-photo statistics exactly and independently audits81 total
comparisons. Original/subset V64-minus-V63 sRGB gains are+.02598/+.02585/+.02600dB,
with positive source intervals. These are known-source-family sensitivities,
not certified scene independence or evidence about training-seed uncertainty.

The no-promotion decision follows both the measured means and actual native
views. Weak dark texture, coarse saturated colors, soft real detail and36–37s
restoration times for102MP leave the full SOTA/real-quality/10s objective unmet
or unproven. The next controlled quality question is the separately prepared
[normalization augmentation](normalization-augmentation.md), which still lacks
trained-quality evidence.
