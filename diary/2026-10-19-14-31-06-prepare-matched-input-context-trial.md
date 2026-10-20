# Prepare an input-context-only training experiment

The prior goal turn made concrete progress: both original20k training endpoints,
full ten-stage/native-data review and actual TF32x3 GPU review completed and
were published. Neither model is promoted; TF32x3 accuracy passes but resident
speed is worse. Those jobs and exact owners are now terminal. The full PROMPT
quality/real-superiority/100MP10s objective remains incomplete.

The next fixed comparison isolates extra input context with identical central
supervision: common native320 physical batches, forward256 versus320, common
loss256 and unchanged native256 validation. The extra32px border matches the
existing overlap64 serving margin. This is not an equal-compute trial, a new
model architecture or a claim that context caused the prior failures. The
recent AIM RAW challenge provides motivation for a context check, not a
reproduced result. A fresh survey also distinguishes JPEG-conditioned MambaRaw
coding from this task; no upstream model code/weights were incorporated.

The new default-off training context helper crops full RGB/validity fields in
native coordinates and packed RAW/variance/auxiliary mosaics at half resolution,
without interpolation, RNG draws, metadata changes or Bayer-phase shifts.
Losses see exactly the same central region. The actual trainer logs source,
forward and supervision hashes separately, retains selected-domain loading and
rejects changed context geometry on resume. Validation size stays independently
fixed so the unchanged8x held-out corpus is not stretched or subsetted.

The common50912-source training-only subset uses existing4x caches >=640px in
both dimensions. The33955 smaller sources are excluded from both experimental
arms; no val/test membership, new Commons890/public-RAW18/private150 admission,
source pixel, original capture or working default changes. Metadata selection
and32 real cached-photo geometry/PSF/area2 checks pass, including marginal-size
caches. Their full sampled cache SHA/dtype/shape and finite contiguous F32
outputs verify; this is not a rehash of all50912 caches. The original full
corpus remains intact. GFX3879/3880 and siblings stay outside training.

108 CPU regressions pass in22.22s, including all-CFA physical alignment,
identical central loss/auxiliary fields, no outer-target/gradient leakage and
actual tiny-trainer model/EMA/AdamW/RNG restart equality. Eleven additional
protocol guards pass in.02s. An early integration fixture used an invalid20px
validation size; it was corrected to valid64/48/32 geometry, and config parsing
now rejects unsupported source/validation dataset sizes before IO. No genuine
quality run occurred in that failed test. Existing default/grouped paths pass.
Ruff passes. The cohort generator's executed bytes remain unchanged and bound.

V86/V87 configs and declared original4000 criteria are prepared from genuine
V63 original20k EMA, seed54, B16/BF16 with fresh optimizer/EMA and no additional
RAW head. CPU/B1/source64 and intended CUDA/B16/source32016-update discarded
preflights must pass before full training. They preserve the original4000
schedule and test actual incoming model/loss fields, identical full source/core
batches, genuine frozen DINO, final finite91/91/89 states and RNG/source equality.
All heavy new roots use the external SSD, with explicit resource/owner bounds.
No full training, quality inference, protected-final scoring or promotion is
claimed at this preparation boundary.
