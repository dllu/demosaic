# Matched coherent CFA estimator trial

Recorded: 2026-11-03T13:36:40-08:00 (America/Los_Angeles).


The previous goal turn was progress: the target-informed diagnostic established
per-bin spectral headroom and an exact-quiet false-lattice counterexample. This
turn tests known CFA transport and green common/difference evidence as an input
coordinate system, with richer support summaries from the same observed RAW.
No claim of improved quality is made before the fixed endpoints are reviewed.

Added `LateSpectralAlignedMatrixDetail` and `LateSpectralCoherentDetail`.
The first has31,409 parameters and exactly the same twelve initial tensors as
V148. The second has33,353 parameters, copying all existing weights and appending
nine zero local-input columns. Known physical sampling offsets align the four
phase spectra, then red/green-common/green-difference/blue coordinates condition
the estimator. Native conjugate/norm projection happens after mapping the matrix
back into physical slots; its non-unitarily-invariant1/inf gauge is not moved.
The contextual arm adds local observed green-energy summaries at packed9/33/129.
These are features, not whitening, calibrated probabilities or flat guarantees.

All53 scalar/matrix/coherent component tests passed in2.83s, including independent
NumPy carrier/basis/gain/overlap/average calculations, allCFAs, constants,
initialization/RNG/meta behavior, CPU FP32/BF16 continuation, CUDA parity and
finite gradients. This is an actual terminal observation; no stdout file is
invented. Native control's support-input hook refactor matches the old frozen
forward and archived V148 pixels exactly on28 cached cases (56 forward-function
evaluations) over256/384/512/768 contexts and allCFAs/standing real controls.

Three fresh heads passed discarded CUDA10 each with genuine8+2 optimizer reload,
all twelve finite/nonzero tensor gradients, and nonzero context-column gradients
(maximum2.619684e-9 during smoke). Peak allocatedCUDA4.503814GiB. Production starts
fresh afterward; the old trained V148 weights are used only for compatibility.

V149 adopts all1,000 existing V148 input/parent/target batches (4,000 old
observations). No noise construction, source-photo lookup, parent or DINO forward
is needed. Source/loss/geometry, seed, LR/schedule, clipping, EMA and1k horizon stay
fixed across native matrix, aligned matrix and aligned/context arms. All six
final raw/EMA endpoints cover the retained798 cases, not fresh independent
validation. The original16 review photographs and both GFX captures/siblings
remain excluded from training. Originals remain untouched, with no RAW/dataz
access. Runtime memory/disk reserves and12GiB CUDA quota remain enforced.

Prepared/froze the six-endpoint review, independent scoring and66 native figures,
with actual blank/DC/spatial errors alongside change energy. The fixed42 old
ROI/display templates generate24 repeated-cell triplets plus42 comparison boards.
Both standing real scenes, both extra-mesh priors/windows and both JPEGs are
included as qualitative references, never exactGT. The reporting preflight
passes40 old parent cases (32 mixed+8 all-CFA present/absent mesh), maximum
formula difference1.24e-13, with CUDA uninitialized and no new neural/noise calls.

Initial preparation incorrectly assumed every retained case had `output_shape`.
It stopped before creating the trial or doing GPU work. Corrected the storage
estimate to read cached parent NPY headers; failed source/receipt are preserved.
No scientific model, input or endpoint changed. Production uses the first frozen
V149 plan/controller/worker; no running worker was replaced or restarted.

Training and queued review remain active at the preparation snapshot. Quality
and actual native viewing remain pending. A useful result must improve detail
and actual quiet-region behavior, rather than merely change parameterization or
pass engineering checks. The broad objective remains active and unmet.

[Component/protocol](../docs/coherent-phase-estimator.md) ·
[Preparation evidence](../docs/results/v149-coherent-phase-preparation-v1.json).
