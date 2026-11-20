# Regional weak-wire training from Local 50k

**Training completed November 19, 2026.** Two matched continuations
test whether a local weak-direction loss recovers contrast that is
averaged away by a whole-crop loss. Both arms also get explicit
supervision where that direction is absent. The
[1,024-update endpoint review](local-regional-wire-1024.md) finds lower
continuing-strand error and weaker second-direction response. The
[fixed photo panel](local-regional-wire-1024.md#fixed-photo-panel)
places both final EMAs about 0.037 dB below Local 50k. The
[512-update review](local-regional-wire-512.md) and
[128-update review](local-regional-wire-128.md) retain earlier checkpoints.
[Launch receipt](results/local-regional-wire-v1/launch.json) ·
[Frozen protocol and qualification](results/local-regional-wire-v1/launch-evidence.tar.xz).

The [32-group gradient audit](local-regional-wire-gradient-audit.md)
finds that the weak terms often oppose the exact-flat and absent-direction
losses through the shared weights.

## Parent and matched training data

Both arms start from Local 50k EMA
`62f4e9ce84075c8df1a254a1889033b5787133e8c98c63e0ec3d174a94734959`.
Local 50k reduces independent-draw fine-increment and exact-flat RMS
versus Corpus 100k, with less target-aligned fine response. Earlier
[whole-core signed and continuing-wire training](local-continuing-wire.md)
improves direction-specific recovery, with more intact or flat error.
The new comparison starts from the quieter larger-corpus endpoint.
[Local 50k comparisons](scene-50000-controlled.md).

Each arm received the same **1,024 updates on 1,024 distinct
photos**, 512 natural and 512 with planted weak wires. The sources
come from the approved 90,692-photo continuation corpus. They are
disjoint from the previous paired continuation schedules and the
frozen native review panels. All four Bayer layouts, ISO400 and ISO6400,
and coupled and independent noise within each pair are balanced.
Of the wire groups, 400 keep the stronger direction through the
weak gap and 112 have a gap in both directions. The CPU audit checks
all 512 wire layouts for intact and gap projection support.

Each update uses six 256-pixel native observations. These include
two independently redrawn present/absent pairs, one flat control and
one ordinary photo crop. The 6,144 observations per arm are generated
from a fixed source and seed schedule. CUDA BF16 neural forwards,
FP32 camera paths and losses, and frozen DINO are shared. The full
local restoration trunk is trainable. The LR uses a 64-update warmup
to `5e-6`, then decays across the full 1,024 updates. Both arms store
raw weights, EMA and optimizer state at the same milestones.

## Matched loss comparison

The shared losses are absolute reconstruction, mean-first frequency
error on the paired increment, independent-redraw stability, a signed
continuing-wire term, and an absolute weak-direction penalty where the
weak strand is absent. The last penalty projects each draw's error
against the weak carrier quadratures, using the exact surviving clean
background for supervision. This includes both the true gap and the
paired observation without the weak strand.

The **whole-core arm** applies the inherited signed weak-response loss
on the 96-pixel core. The **regional arm** measures the paired error
in nine overlapping 48-pixel neighborhoods. Each local contrast
projects out an affine background and the first three harmonics of
the strong direction before penalizing weak-direction error. The
preserved phase and geometry are available from the simulation during
training. At inference both models take one noisy Bayer observation
through the existing Local 50k path.

The regional term uses weight 0.710, versus 1.6 for the global term.
The median ratio of the two initial output-gradient norms is measured
at the same Local 50k predictions on the three reserved wire pairs
with valid whole-core supervision. The fourth pair is clipped in the
whole core. The regional loss can still use valid individual tiles.
The qualification also verifies identical initial predictions,
finite update gradients and an unchanged DINO checksum. Its 42.4 s
wall time includes saving and hashing qualification checkpoints.

## Frozen endpoint review

The scoped review binds 24 exact natural photos, 24 exact wire
fields, and the 32-photo off-grid transfer. The standing GFX review
binds DSCF3879/3880 at ×4 and both cab ROIs on DSCF3842/3835 at ×4
and ×16 under both established noise profiles. The separate camera
JPEGs and independent ISO100 AHD references are bound in the
review plan. Training completion, numerical evaluation and native
viewing will be recorded as separate states.

The endpoint camera and photo panels use the same frozen canonical
inputs as the other full-model comparisons. Current coverage is in
the [PSNR history](performance-history.md).
