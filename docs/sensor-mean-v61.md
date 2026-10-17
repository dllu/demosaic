# Full-restoration multiscale sensor-loss trial

V61 is training to its first 1,000-update review boundary. It tests whether
coarse measured-CFA supervision reduces remaining color/low-frequency errors
without sacrificing photographic detail or paired-real accuracy. The
[completed V60 comparison](wide-flat-palette-full4k-review.md) improves bright
high-saturation fields, but retains moderate-saturation errors and lower paired
primary means than V43. No V61 quality gain is established by its preparation.

[Actual launch, frozen source/config/data hashes and logged-input matches](results/sensor-mean-v61-first1k-launch.json).
[Complete CPU/CUDA engineering evidence](results/sensor-mean-v61-preparation.json).
[Configuration](../configs/dino-convnext-palette-sensor-mean-b16-v61.yaml).

The completed V60 run supplies the matched control; it is not trained again.
Both begin from the same mature V58 step10000 EMA, SHA256
`cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3`,
with fresh AdamW/EMA, seed 48, batch 16/native 256, LR 2e-5/warmup 100 and the
same planned 4,000 updates. Both retain the 8-stop smooth palette, original
Commons 40,170/native 128/paired 32 manifests, domain proportions, 4×→geometry/
PSF→area2 path, noise/ADC and original 8× validation. All restoration parameters
train; the pinned DINOv3 backbone remains frozen. No new parameters or inference
operations are added. The reviewed 66,934-image corpus remains separate.

| Setting | Completed V60 | V61 |
| --- | ---: | ---: |
| `multiscale_sensor_weight` | 0 | 0.01 |
| First review / original planned updates | 1,000 / 4,000 | 1,000 / 4,000 |
| Other training settings | Shared | Shared |

Only the loss coefficient changes; run path and experiment notes distinguish
the artifacts. At the first boundary, the controller checks all 41 logged
domain/LR/batch hashes against V60's preserved first1k log and freezes the whole
model/EMA/AdamW/RNG checkpoint. Matching logged observations does not prove every
unlogged batch was separately hashed or CUDA optimization is bitwise repeatable.

The existing loss samples predicted RGB at the actual CFA phases and pools
4×4, 16×16 and 32×32 packed-phase blocks, corresponding to 8/32/64 sensor pixels:

`standardized error = sum(prediction − clean CFA reference) / sqrt(sum(input variance))`.

It averages a Charbonnier penalty in these input-noise units across scales.
Variance comes from the clean reference and supplied shot/read values. This is
an independent-input-noise scale, not posterior restoration covariance.
Synthetic blocks containing clipped/out-of-range targets, incomplete real
reference blocks and ADC-only draws are excluded. Real references use measured
CFA samples, without new AHD fine-detail supervision; reference noise and
registration error remain limitations. The original objectives still apply.
This term therefore does not directly supervise ADC-only color errors.

The earlier [V26/V27 experiment](scale-aware-supervision.md) found no useful
gain with this coefficient while training only a 27,696-parameter coarse
correction branch over a frozen parent. V61 instead trains the complete
32,904,704-parameter restoration network, with the same architecture and
initialization as V60. The old negative evidence is retained; a different
trainable parameter set does not guarantee that this intervention will help.

## Executed engineering checks

The relevant CPU tests pass: 16 passed, with one CUDA test skipped because CUDA
was hidden. The CUDA-enabled physical-loss suite passes all 13 tests. Coverage
includes four CFA patterns, noise-unit scaling, phasewise zero-mean error,
measured-only references, invalid/clipped/ADC exclusions and both objectives.

The genuine-parent CPU fixture uses batch 1/native 64/FP32 and all three data
domains. Four uninterrupted loss-on updates match two plus two resumed updates
exactly in model/EMA/AdamW, model configuration, Python/Torch/CUDA RNG, best and
step state, plus numerical training logs. The genuine CUDA fixture uses batch
16/native 256/BF16 and all three domains: losses, gradients and all 91 model /
91 EMA / 89 AdamW states are finite. Saved step-2 state restoration is exact,
and two portable EMA photo predictions match reconstructed EMA inference exactly.
These checks do not claim bitwise-identical CUDA training after a restart.

All four observation hashes match loss-off control in each fixture. The extra
term contributes finite optimization pressure, which is not evidence of improved
restoration. Fixtures force smooth Commons samples and disable data workers;
production uses the unchanged V60 fractions and worker counts. Peak CUDA
allocation in this discarded fixture is 7.200 GB, not a production speed result.

Actual wrong-review and live-owner invocations reject before output creation
or CUDA initialization. The executed operators are frozen separately from the
unchanged model worktree. [Preflight driver](../scripts/preflight_sensor_mean.py).

## Required quality review

Review against V60 at the same boundary using full 427-photo and procedural
scores, known/unseen measured-CFA development panels, the fixed 1,176-observation
hue grid, selected CPU colors and weak carriers. Reuse verified saved control
predictions/scores where possible. Include at least two native noisy/denoised/
exact-GT photographic triplets and the standing DSCF3879/DSCF3880 sky, building,
foliage and chain-link-fence regions. The independent ISO100 capture and other
camera comparisons must retain their accurate non-GT labels.

No automatic continuation or model promotion follows the first boundary. Any
later updates retain the original schedule and whole state. Protected-final
scoring stays closed; general color repair, real superiority, SOTA and the
100 MP / 10-second objective remain unproven.
