# Learning fine detail that survives independent noise

The [first paired luminance head](paired-luminance-detail.md) adds
0.47 percentage points of ISO6400 target-aligned response on 64
photos. Its increment error falls with coupled noise and rises
with independent noise. This study tests whether a single-frame
head can retain that response while reducing the part of its
error that varies across physical redraws.

## Matched training

All three heads start from the paired EMA at checkpoint
`02f8d5e6664bd580bafe2abeb3b8584b070b60bfadfefaff587cadd8bd643d7f`
above frozen Corpus 100k. Each learns the delivered luminance
correction through the same two-window Bayer support. The three
heads see the same camera observations, use the same AdamW
schedule and keep the same absolute, flat and signed-increment
supervision. Two heads also penalize differences in reconstructed
present-minus-absent detail between independent repeats, at
weights 0.25 and 0.75. Each forward pass sees one noisy observation.

The fixed schedule uses 1,200 updates on 2,400 distinct photos
additional to the first paired-head run. Each photo supplies two
independent complete draws of a present, absent and exact-flat
target triplet. Within a photo, both draws use the same coupling
law. The training set has 150 photos in each ISO, Bayer layout
and coupling cell, for 14,400 sensor observations per head.
This balances the [joint ISO and layout coverage](paired-luminance-detail.md#noise-level-and-bayer-coverage)
that the first run missed. The source manifest excludes both
standing GFX families and the fixed evaluation sources.

The raw and EMA weights are saved separately. Three qualification
updates ran on six sources outside the training schedule and
verified finite gradients, identical initial head outputs, exact
repeat targets and a frozen parent. The 1,200-update run is active.
[Frozen plan and qualification evidence](results/paired-repeat-stability-v2/preflight.json).

## Native evaluation design

The fixed evaluation includes the original 64 held-out photos and
32 additional held-out photos from the frozen photo cohort. Each
source contains a present, absent and exact-flat target at both
ISO400 and ISO6400. There are three independent complete draws
per within-pair coupling law. The original panel keeps its first
archived observation for each condition, with identical clean
targets and two new physical draws. The additional photos use
three new draws.

Fine error is measured on the 96×96 core in the 1/8 to 1/3
cycles/pixel luminance band. On each source, the mean product of
different-draw errors estimates error shared across redraws.
The sample variance estimates the draw-sensitive part. These
terms sum to the mean squared error of the three individual
predictions. The report will also score exact-flat texture, low
bands and color bias, with source-level resampling. The matched
control, original paired head, frozen Corpus 100k and V120 enter
the comparisons. Both standing GFX families have fixed native
ROIs and matched render settings. Their ISO100 captures and
cab JPEGs are qualitative references.

## Starting model on 64 photos with three redraws

Before the new heads finish training, the frozen starting EMA
was evaluated at ISO6400 on all 64 original sources with three
complete redraws per law. In the earlier [two-draw comparison](paired-luminance-detail.md#matched-64-photo-results),
the two draws used different within-pair laws. This replay holds
the law fixed when estimating the variance.

| Guarded starting head minus Corpus 100k | Coupled | Independent |
| --- | ---: | ---: |
| Target-aligned response (percentage points) | +0.459 | +0.469 |
| Fine-increment RMS (DN16) | −1.087 | +0.325 |
| Fine RMS on the present target (DN16) | −0.164 | −0.193 |
| Exact-flat fine RMS (DN16) | +0.092 | +0.087 |
| Repeat-shared fine-increment error (DN16²) | −301.1 | −295.3 |
| Fine-increment variance between draws (DN16²) | −38.7 | +404.6 |
| Mean fine-increment squared error of a single draw (DN16²) | −339.8 | +109.3 |

For independent pairs, the source-bootstrap 95% intervals are
[−402.2, −203.1] DN16² for the change in shared error and
[270.6, 563.6] DN16² for variance. The coupled variance
interval is [−59.4, −22.2] DN16². The shared-error reduction
is similar under both simulated coupling laws. A rise in draw
variance offsets it only with independent pairs. The existing
head slightly improves the fine-band fit to the single present
target under both laws, with extra variation on exact-flat
controls. Repeat-stability training tests whether it can reduce
that independent-draw cost. The table contains only the frozen
starting model and its parents.
[Metrics and source intervals](results/paired-repeat-stability-v2/start64-summary.json) ·
[Per-source inputs and frozen analysis](results/paired-repeat-stability-v2/start64-evidence.tar.xz).

On the 32 additional photos, independently drawn ISO6400
pairs reproduce the tradeoff. Aligned response rises 0.390
percentage points, shared error falls 183 DN16² and variance
rises 315 DN16². Fine-increment RMS rises 0.462 DN16 and flat
RMS rises 0.049 DN16. The change in single-present fine RMS
is +0.025 DN16 with an interval spanning zero.
[All 96 starting-model results](results/paired-repeat-stability-v2/starting-all96-summary.json) ·
[Per-source evidence](results/paired-repeat-stability-v2/starting-all96-evidence.tar.xz).

## First checkpoint at 300 updates

The first 16 original photos have an early ISO6400 numerical
check with three redraws per law. The three EMA heads share
the checkpoint `1940c84a459b5815d48e7c0b7b19dd940d682e5d663a11b4a0eedd0bf54281b1`.
Compared with the matched control, the higher repeat weight
reduces independent-draw fine-increment variance by 154.4
DN16² and raises shared error by 121.4 DN16². Fine-increment
RMS decreases 0.114 DN16 and exact-flat fine RMS decreases
0.029 DN16. Target-aligned response falls 0.203 percentage
points. In the coupled comparison, target-aligned response
falls 0.190 percentage points and increment RMS rises
0.470 DN16.

Scaling the control correction to 25.5% of its strength gives
the same pooled independent-draw response as the higher-repeat
head. Against this response-matched control, that head changes
increment RMS by +0.003 DN16 [−0.012, 0.023], flat RMS by
+0.0001 DN16 [−0.0014, 0.0026] and draw variance by +6.2 DN16²
[−5.4, 20.5]. The scalar was fitted on these same 16 sources
as a descriptive control. Most of the apparent variance gain
at this checkpoint can be reproduced by weakening the correction.
The 96-photo endpoint evaluation and actual GFX viewing are pending.
[Interim metrics and source intervals](results/paired-repeat-stability-v2/checkpoint300-summary.json) ·
[Frozen checkpoint evaluation](results/paired-repeat-stability-v2/checkpoint300-evidence.tar.xz).

The [projected repeat follow-up](paired-shape-stability.md) tests a
repeat term whose value stays fixed when the starting correction
is uniformly weakened. Its eventual response matching uses
the original 64 photos to set the scales and the additional 32
to measure transfer at those scales.
