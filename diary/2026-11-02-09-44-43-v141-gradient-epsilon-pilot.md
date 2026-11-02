# Separate small-gradient smoothing with matched V141 training

Recorded: 2026-11-02T09:44:43-08:00 (America/Los_Angeles).

Previous goal turn made concrete progress:3abb59f completed/published V1401k
native and exact-flat review, with no useful new mesh recovery. Rechecked the
current tree/process table: those workers exited; no old training was live.

Measured V140's trained memory amplitudes on six retained reconstructed CPU
branch contexts. Exactly6 partial branch forwards, no full-model/DINO/VST or
new noise/RAW/target reads. Memory-return RMS before final projections is
.97–1.60% of combined point+patch token RMS; final projected offset RMS
5.78e-6–3.54e-5 feature units. Not a causal RGB explanation. All learned branch
source modules match the actual trained snapshot. Collector was subsequently
formatted and its already-serial hook storage explicitly bound; preserve its
first receipt/activation bytes and historical operator hash. Rechecked every
saved RMS via independent NumPy reduction with no neural replay.

Implemented separate gradient_charbonnier_epsilon. Missing/None exactly inherits
pixel epsilon; new explicit value changes only rendered spatial-gradient errors.
Direct/grouped/mean paths and source traces share it. Serialize effective values;
reject changed pixel/gradient scales before constructing a resumed model.
Production defaults unchanged. Paired objective unchanged. No inference option.

V141 fixes gradient epsilon3e-5 versus savedV1293e-4, all other coefficients/
pixel epsilons unchanged, same V120/90782-27/seed70/quota.5/zeroPSF/native256B16/
BF16/LR1e-5/warm100/original1000 horizon. No data or architecture confound against
that control; all1000 clean/noisy batches must match. Pixel loss still controls
absolute/color error; gradient loss matches zero variation on true flat targets.
This is a hypothesis to train/test, not a guarantee of detail or hallucination safety.

70 tests pass, including default exact loss/gradient behavior, gradient-only
changes, correcting missing weak texture and penalizing invented flat texture,
actual grouped mixed training, legacy/default inheritance and exact2-step
versus1+1 model/EMA/Adam/RNG. Both fresh CPU128B1 and CUDA256B16 checks pass16+2,
all36 prepared batches exactly V129. The first CPU/CUDA outputs match4,259,840
old zero-offset V140 parent values exactly.91 model/EMA tensors,89 Adam states
finite at18. Two changed-policy cases per device reject before construction.
Fresh production is live under original1k/8h,12GiB allocation/32GB runtime floor.

Fixed102 candidate native/shadow/faint/GFX calls plus48 exact-flat calls before
seeing outputs. Reuse408+48 controls, all150 observations/750 input arrays and
111673344 old prediction values checked. Both protected GFX pairs/JPEGs/siblings
stay out of training; both mesh priors, foliage/fence/sky/building included.
Private flat operators change labels and explicit relocated root only; preserve
V140 public operator bytes/guards. Faint reader now accepts a declared primary
completion marker while retaining its old default. Quality remains unmeasured.

[Current implementation/pilot](../docs/v141-gradient-epsilon-pilot.md) ·
[Checks and declared review](../docs/results/v141-gradient-epsilon-setup-v1.json) ·
[Memory amplitude measurement](../docs/results/v140-memory-amplitude-v1.json).

A further34 noise-pair/faint-analysis tests pass (104 total across the two
suites). Production at350 retains all batch matches and about7.05GB peak CUDA.
