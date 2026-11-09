# Physical multiscale CFA support

Recorded: 2026-11-08T17:19:25-08:00 (America/Los_Angeles).

Previous goal turn: progress through completed V199 gate interventions, native
viewing and publication. Simple shared/positive gates retain building/flat
artifacts; unnormalized constants mainly shrink useful correction. This turn
implements physical cross-scale support rather than another posthoc gate rule.

Added two neural-source files, preserving all 105 earlier files and old
checkpoints. Each CFA phase's local affine+cos/-sin fit now exposes nominal
amplitude covariance G† H G†, including off-diagonal heteroscedastic projected
noise. Integral trace and complex pseudo-variance recover H. Canonical RGB
amplitudes retain own-color measurement; green's independent-RAW nominal center
trace averages its two phases with factor 1/4. Squared interpolation of the
square-root center trace is a conservative Cauchy bound with overlapping boxes,
not exact interpolation variance. Correlated anchor errors and data-dependent
selection are not modeled; none of these quantities is calibrated confidence.

The new twelve coordinates compare physical RGB amplitudes of 65 with 33 and 17
using bounded complex agreement, with nominal powers and a one-DN16 squared
amplitude floor in the denominator. The inherited 24 contexts, eight innovation
bins 1/64…1/3 and physical 65 RGB synthesis basis remain. The fresh 36→16→3 head
has 643 parameters/four tensors, adding 192 parameters. Old 24 input columns retain
their initialization; extra columns and final gates start at zero. All 193 V195
Whole EMA anchor tensors stay frozen, 197 full state tensors. This changes features and
capacity together, so future quality is a combined architecture comparison.

The initial 26 mathematical contracts pass. The first combined fixture run
passes 30 but fails 4 training-mode assertions because replacing frozen stubs gave
them default training=True. Calling train() after fixture substitution fixes
the fixture; no model formula changes. The retained second log passes all 34
focused contracts, including direct QR amplitudes/every covariance entry,
DC/Nyquist ranks, affine and variance identities, four Bayer layouts/both dtypes,
native basis agreement, exact overlap operators versus interpolation bounds,
phase/bounds, initial anchor equality, isolated extra-column learning and ADC.
Both logs survive. Ruff passes.

The source-sealed V200 admission owner PID1988591/create1794187258.09 is terminal
and passes eight actual initial anchor parities. Seven CPU/GPU comparisons
check 325,582,848 context and 54,263,808 physical-wave values, plus 4,993,152 nominal
covariance entries across all three scales. Seven nonzero head comparisons
activate the extra columns. Two training-only mesh/mixed updates match CPU
head gradients, with 192 extra-column nonzero gradients on update 2. A strict
model/Adam/EMA/CPU-CUDA RNG restore after update 1 precedes 2. Peak CUDA allocation
is 10,466,198,528 bytes. No protected optimizer input, source/noise draw, parent/
DINO inference, original/RAF/dataz access or external write occurs. The frozen
CPU inspector passes four raw/EMA states, 772 unchanged anchor tensors and two
Adam-state checks without CUDA initialization. Probes are never initializers.

Prepared and launched the full 900-update V200 trial with fresh Adam/EMA 0,
initial full-module hash
`b29621f865f91333498aa0365cdba21d8350711ac358e784ca3f4e11ee94ca66`.
Same 1,000 cached rows/3,600 noisy images/100 ADC skips, seed 202611080198,
V195 Whole ten-term objective (0.50 coherent), pair units, masks and LR/WD/clip as
V198. Controller PID1991540/create1794187487.76 and worker
PID1991545/create1794187487.81 are confirmed live after launch. Actual row 8
model/Adam/EMA/CPU-CUDA RNG restoration passes and continues at 9 without
repeating the prefix. Planned storage is 2 GiB local above a 40 GiB reserve and zero
new external allocation. Reuse existing immutable arrays and factored snapshots.

Training and quality remain pending. Full trace/checkpoint audit, both raw/EMA
endpoints on all 822 cases and native 100% comparisons are required. Retain both
protected GFX families, main sky/building/foliage/coarse fence, both fine cab
ROIs/noise profiles/JPEGs, and accurate independent-reference labels. All
captures/JPEGs/siblings remain excluded from training. The fine-detail/clean-flat
goal remains active; no image-quality improvement is claimed from admission.

[Implementation and limitations](../docs/scale-supported-cfa-wave.md) ·
[Engineering evidence](../docs/results/v200-scale-supported-CFA-preparation-v1.json).
