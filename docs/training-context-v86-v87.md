# Fixed V86/V87 input-context comparison

This trial asks whether surrounding RAW pixels help the existing mature
DINOv3/RGB model learn a better restoration for the same supervised pixels.
Both arms prepare the same native 320 observation and supervise its central
native 256 region. Control forwards only that central 256 observation. Context
forwards native 320 and crops its prediction and auxiliary mosaic to the same
central 256 region before every loss. The intervention is the extra 32px border
on each side, including its effect on existing model normalization/features.
There is no additional clean-target supervision, new architecture or DINO weight.

The [AIM 2025 RAW-denoising report](https://arxiv.org/html/2510.06601v1#S5.SS1)
describes progressive training sizes and a train/test resolution mismatch.
That motivates checking context here; it does not identify the cause of our
detail loss. Its RAW-to-RAW task, training budget, synthesis, masking and
additional data differ. This experiment is an independent fixed-context test,
not a reproduction of the report or a progressive-size schedule.

## Matched source, noise and supervision

The common Commons subset contains 50,912 existing train sources with 4× caches
at least 640px in both dimensions. All 33,955 smaller train sources are excluded
from **both** arms to avoid upsampling or changing the final 8× reduction.
No validation/test source is admitted. This restriction is geometric, without
model-output or image-quality selection. It is an experimental subset, not a
replacement for the full corpus. The separate 8× validation manifest remains
unchanged at native 256. [Frozen cohort and 32 actual CPU source checks](results/training-context320-cohort-v1.json).

Both arms retain native 128 captures/106 groups and paired 32 scenes, the .25/.25
native/paired fractions, procedural/flat fractions, palette, physical noise,
camera transport, negative read noise, sensor-valid targets, losses,4×→geometry/
PSF→area2 and source-step RNG. Future Commons890/public-RAW18 and private150
remain outside this trial. Cached GFX3879/3880 and siblings remain excluded.
The paired AHD and standing ISO100 RGB references are independently demosaiced;
neither is exact RGB GT.

Native/paired observations also start at 320px. Full-resolution targets and
validity masks use native coordinates; packed RAW, variance and the auxiliary
mosaic use half-resolution coordinates. Central offsets preserve Bayer phases.
No image interpolation follows the existing final area2. Cropping consumes no
random numbers and never alters WB, matrix, noise coefficients or source data.

Actual forward hooks and loss wrappers record the incoming fields. Every
recorded pair must have identical full source batches and actual central loss
batches, with different intended forward extents. Domain choices and LRs must
match; final Python/CPU/CUDA RNG states and source archives must match. Logged
source, forward and supervision hashes are separate. These finite observations
are not a replay of every unlogged sample.

## Training and boundaries

Both fresh arms initialize from the genuine V63 original20k EMA
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
The official frozen DINOv3 ConvNeXt-Tiny pyramid and mature pretrained DRUNet
RGB backbone stay unchanged. Each arm has a fresh optimizer/EMA/RNG, seed 54,
B16, BF16/channels-last and deterministic execution. LR is 1e-5, warmup 100,
original 4000 updates with the existing 10% cosine floor. The common budget is
64,000 example draws and identical 256px supervised regions per arm. The larger
forward consumes more compute; this is not an equal-compute comparison.

Use final `last.pt`/retained step4000 endpoints, not validation-selected weights.
Retain 1000/4000 for integrity. Intermediate validation is ordinary trainer
bookkeeping and cannot shorten, select, extend or promote this trial. Actual
CPU/B1/source64 and CUDA/B16/source320 16-update checks must pass before a full
launch. CPU uses forward32/64 and common loss32; it is an engineering check,
not the production geometry or a quality result. CUDA uses the intended
forward256/320 and common loss256. All these checks retain the original 4000 LR
horizon and discard their weights.

Full training requires 48GiB available for 60s before each arm, 24GiB CUDA quota,
root128GiB/external500GiB launch/active disk reserves and 14400s per arm. Resource
waiting is bounded at 14400s. The trainer's available-memory check uses 32GB;
the controller stops only its own exact worker below 24GiB, on disk exhaustion
or timeout. A controller SIGTERM does not promise a new checkpoint. Preserve
all existing files and failures; no automatic retry, continuation or promotion.
Runs and new heavy outputs live on the external SSD.

## Declared final quality review

Freshly score both final EMAs and genuine V63 in FP32 on the unchanged known4,
unseen5 and full 427×seven-conditions×four-CFA development protocols, plus the
separate 16 procedural sources. Keep all conditions, canonical camera-linear
adverse scores/conventions, 418/416 source sensitivities, complete analytic,
ADC/color/highlight panels and retained V43/RawNIND comparisons with witnesses.
The photographic primary retains its native 256 inputs/central160 scoring ROI;
it measures the learned-weight effect at that input field and does not test a
larger photographic serving field. The existing native 512 camera/GFX panels
provide the larger-field camera/qualitative checks. No new observation padding,
larger-field synthetic protocol or retrospective metric replacement is implied.

A context-benefit claim requires a positive lower 95% source-bootstrap bound
for context−control photographic PSNR, known/unseen mean losses no greater
than .03dB each, and no new visible failure in the fixed views. Descriptive
weak-detail benefit additionally requires signed in-phase gain improvement of
at least .05 in **both** fixed high-noise cases, flat spatial-luma RMS at most
1.25×control, and no individual ADC layout/draw gain loss greater than.05.
Keep all 192 individual contrasts and 12 group means; averaging cannot hide a
case failure. These are fixed analytic tests, not photographic confidence bounds.

Each checkpoint separately needs at least +.05dB versus fresh V63 on photo,
known4 and unseen5, positive respective 95% lower bounds and photo-SSIM loss
at most .0001 before full-frame eligibility. Complete actual native viewing and
no new color/detail/highlight failure are also required. Numerical passes alone
do not establish global SOTA or authorize promotion. The single shared seed
and source bootstrap do not measure training-repeat uncertainty.

Reports include at least two identical-ROI native 160 noisy/restored/exact-GT
triplets per checkpoint, source/conditioning/exposure/checkpoint hashes and
attribution, without resizing. Inspect standing GFX sky/building/foliage/fence
plus sign/platform, accurately labeling the different-ISO/aperture/time AHD
references. Keep representative README images on V43 unless a stronger model
is fully verified. Only eligible checkpoints get a separately bounded full
101.996MP FP32/RGB16/export/native/timing check. Protected-final scenes stay
closed. Neither engineering nor training completion satisfies PROMPT.md.
