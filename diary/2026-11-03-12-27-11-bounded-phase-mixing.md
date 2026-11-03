# Bounded phase mixing with a matched scalar control

Recorded: 2026-11-03T12:27:11-08:00 (America/Los_Angeles).

The previous turn completed V147 and its controlled support intervention. Full
support exposed a worse proposal: weak response fell further and noisy flats
showed false fine grid/grain. That changes the next action from adjusting support
to testing whether an estimator that combines phases can do better.

Added `LateSpectralMatrixDetail`, a bounded complex4×4 operator on the same
observed-minus-parent spectrum. Conjugate frequency pairing gives real-image
synthesis. A computable induced-norm bound includes scalar diagonals while
limiting per-bin coefficient energy. This is not a global RGB or noisy-flat
safety guarantee. Constants remain exactly inactive with arbitrary finite
learned weights. All ten common tensors initialize identically; the replacement
operator starts zero. There are31,409 parameters/twelve tensors. Removed16
unidentifiable constant imaginary biases before freezing this version.

The final32 scalar/matrix tests passed in2.39s, including independent NumPy
descriptors/convolution/matrix math, singular-value bounds, finite gradients at
zero, a coherent-green averaging capacity example, optimizer continuation,
CPU RNG/meta-device behavior and CUDA parity. The earlier preliminary32 passed
before the bias cleanup; no quality result or training run used that prototype.
These are actual terminal observations; no saved stdout log is invented.

V148 is a matched fresh scalar/matrix trial, preserving the V147 data/loss/seed,
common initialization, LR schedule and1k horizon. Legacy scalar, current scalar
and an embedded trained scalar in the matrix family match exactly on28 cases
across allCFAs and256/384/512/768 contexts (84 engineering forwards). Both heads
then passed discarded CUDA10 updates, a genuine8+2 optimizer reload and all12
parameter gradients; peak allocated CUDA memory4,374,891,008 bytes. These checks
validate engineering, not learned quality.

Prepared the single shared replay cache: all1,000 input/target fingerprints
match the immutable V147 trace. Adopted the first40 old observations/parents;
reconstructed the remaining3,960 observations with the same noise realizations
and evaluated990 frozen V143/DINO batches once. Those are not fresh independent
observations. Parent/DINO hashes remain exact. The new matched scalar control
and matrix head both consume these same cached arrays/layout and start fresh.
The old trained V147 weights are not a warm start.

The fixed review covers all798 retained main/mixed observations under all four
final raw/EMA endpoints, independent metrics and58 native figures. The review
uses exact cached parent predictions, adding no DINO/noise calls. Both standing
GFX scenes/priors/JPEGs and siblings remain excluded from training. Actual native
viewing/quality remain pending; no gain is claimed.

A preflight caught an analysis API mistake before any review executed: the
existing error helper returns spatial/DC crop components, not total crop RMS.
The scorer now computes total quiet RMS directly; the independent auditor uses
norm/sqrt(pixel count). Preserved the original frozen postprocessor/receipt and
replaced only its waiting controller with v2. All32 mixed-parent controls pass,
maximum difference1.24e-13. The model, data and fixed endpoints are unchanged.

Controller timeouts now charge observed polling intervals capped at5s, avoiding
charging an entire externally suspended user pause. Exact PID/create-time
ownership,12GiB CUDA quota and52/32GiB admission/runtime RAM checks remain.
The26GiB cache writes only to repo storage; no original-media/RAW/dataz access.

See [the component/protocol](../docs/phase-matrix-detail.md) and
[preparation evidence](../docs/results/v148-phase-matrix-preparation-v1.json).
The overall fine-detail/clean-sky goal remains active.

Both fresh heads subsequently completed1,000 updates on the matched cache. Each
has twelve finite Adam states at step1,000; the paired final checkpoint is
`bf32e14a6f80c82e4369e9d32c75aa4edab75fac77d5e866087c0bd8cffcc576`.
All four final endpoints have finished their798 forward calls, with no parent,
DINO or noise calls during review. Array scoring, audit and native viewing remain
pending at this engineering commit. The preparation evidence retains its original
step740 active-state snapshot.
