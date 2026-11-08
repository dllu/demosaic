# Local phase evidence for matching

**V180 has completed training, quality review and actual native inspection.** It replaces V178's global
coefficient fields with local measurements at the same selected frequencies.
The matching network, zero 80→39 adapter and **2,092,026 trainable parameters
across 142 tensors** stay the same. Both inherited V172 endpoints load all
188 existing tensors exactly; the additional 3,120 weights start at zero.
Actual CUDA parity, gradients, save/restore and CPU/GPU local measurements pass.
A 900-update continuation from V172's real optimizer/EMA history raises mesh
response **15.2–15.9% over global V178**, reaching **4.52–4.55% of constructed
GT amplitude**. Quiet spatial RMS rises 0.76–1.05%; fine cab crossings and
broad/fine mottle remain unresolved. This is a useful detail architecture,
with earlier balanced, quiet and flat options retained.
[Completed comparison](local-phase-evidence-comparison.md) ·
[Native viewer](images/v180-local-phase-evidence-v1/native-viewer.html).

[Model](../src/demosaic/late_local_phase_evidence_matching.py) ·
[24 new CPU tests](../tests/test_late_local_phase_evidence_matching.py) ·
[Native CPU profiler](../scripts/profile_local_phase_preparation.py) ·
[Source bindings and preparation receipts](results/v180-local-phase-preparation-v1.json).

## CUDA admission and continuation

The [separate CUDA entry](../scripts/admit_local_phase_evidence_matching.py)
requires V178's actual terminal, audited, viewed and verified publication.
All 98 existing neural files remain unchanged. Seven cached cases cover four
training domains, ADC, protected sky and cab evaluation. All **14 initial
raw/EMA outputs are bit-exact against V172**, with no protected optimizer use.
The 12 captured GPU feature fields check 170,393,600 coordinates and 42,304
local-center powers against CPU. Maximum differences are **2.98e−8** and
**6.90e−13**; grid geometry and selected bins match exactly. Fixed feature
tolerances remain 1e−4; local powers use 1e−8 absolute/relative tolerance.

Both actual fresh-Adam probe updates have nonzero gradients on all 142 tensors
and all 3,120 adapter weights. Model, 142 Adam states and CPU/CUDA RNG restore
exactly between updates, without replay. Post-update ADC/mixed-zero cells retain
the frozen output exactly; constant RAW evidence stays zero and changing the
other phase cannot change a selecting phase's bins/global power. Totals are
32 wrapper/frozen, 27 matching, 135 sampler and 15 projection calls, with peak
CUDA allocation **6.27 GiB**. The [CPU inspector](../scripts/inspect_local_phase_admission.py)
independently checks all 241 component events and both strict checkpoints.
These two fresh-Adam probe checkpoints are not training initializers.

Single warm parity calls after startup take roughly 0.62–0.63 s versus
0.57 s for the four-image 512px control and 0.29 s versus 0.24 s for the
768px cab context. Cold mesh startup takes 5.01 s. These are observed admission
calls, not repeated throughput benchmarks or full-frame timings.

The [continuation entry](../scripts/train_local_phase_evidence_trial.py)
uses the exact frozen V178 training engine with explicit module-local factory,
root, method and prerequisite bindings. The local class/configuration/source
are recorded even though its initial tensor hash equals global V178. All 141
existing Adam states remain at 900, original moments/network EMA load exactly,
and the adapter starts at zero without Adam history. The cached 1,000 rows,
900 updates/3,600 images/100 ADC skips, seven-term objective, domain weights,
learning-rate schedule and EMA decay match V178. Genuine row8 restoration
passed and continued at row9 without replay. Existing network clocks finish
at 1,800; the adapter finishes at 900. All five checkpoints and the full trace
pass the independent training audit.

Completed V178 control/global-evidence raw/EMA results are retained as
comparisons. They are not rerun; atomic sampler backward remains nondeterministic
under the existing warn-only setting, so this is not bit-exact paired retraining.
Both V180 endpoints use all 822 fixed inputs and the same 36 native cases.
The independent quality audit and actual inspection of all 60 figures/12 triplets
cover mesh, quiet/flat, foliage/building/sky and both fine cab windows. Implementation
admission is separate from those quality results. No new sensor/source/parent/DINO/RAW decode or
original capture access occurs. [Actual admission and launch evidence](results/v180-local-phase-CUDA-admission-v1.json).

The [independent local auditor](../scripts/audit_local_phase_evidence_trial.py)
passes 42 CPU checks, including local-grid geometry, nonfinite/negative powers,
raw/EMA input-only agreement, trace/metric corruption and terminal launch owners.
Its frozen actual entry rejects live training before Torch or checkpoint loading.
The [comparison reducer](../scripts/reduce_local_phase_evidence_trial.py)
passes 14 checks and a complete marked fixture: 15 methods/12,330 rows,
22 contrasts, 2,035 Decimal means and 882 table cells. Both V175 endpoints and
all four V178 endpoints remain available. Four same-endpoint contrasts compare
local against global evidence and control; 18 contextual contrasts retain earlier strengths.

The [native renderer](../scripts/render_local_phase_evidence_trial.py) preserves
all four completed V178 panels, adding two local endpoints at identical source
coordinates and display transforms. A marked old-pixel fixture checks 60 figures,
12 noisy/restored/exact-GT triplets, 8,294,400 newly displayed RGB channels and
43,392,000 copied channels. It is a layout/display check using global V178
pixels under simulated local labels, not V180 quality. Actual mode requires
terminal quality and passed audits and rejects before creating outputs now.
These helpers are frozen separately; the running worker's 725-source snapshot
is unchanged. These preparation fixtures remain separate from completed actual
quality. [Preparation sources and evidence](results/v180-local-phase-comparison-preparation-v1.json) ·
[Actual completion and viewing](results/v180-local-phase-completion-execution-v1.json).

## Local measurements

The [V179 training-input diagnostic](local-phase-support.md) finds higher local
mean power in mesh-containing footprints, with blank means near nominal power
1 and overlapping noisy tails. It motivates giving matching continuous spatial
evidence, without establishing a detector or a restoration gain. Window and
stride defaults were chosen after this diagnostic, not by blind validation.

V180 retains [V178's global selection](phase-evidence-matching.md): each green
CFA phase selects four frequencies from its own RAW and supplied variance,
with the same native 1/16..1/3 cycles/pixel band and conjugate/3×3 suppression.
The other phase cannot change that direction's selection. Only RAW, variance
and CFA layout enter the evidence function; targets, pair labels, references
and the frozen restoration do not enter it.

At each selected bin, both green phases are measured in rectangular windows.
The default side is **65 packed samples, approximately 130 native pixels**,
with centers every 32 packed samples plus the final pixel. Windows truncate
at borders without reflection. Each window removes its own unweighted affine
plane. For its basis Q and complex carrier f, the effective row is
`a = f − Q(QᵀQ)⁻¹Qᵀf`; the measured coefficient is `aᵀRAW` and its supplied
trace variance is `sum(variance × |a|²)`. FP64/complex128 summed-area moments
include the fitted-plane terms. The carrier uses integer periodic phase.

Complex coefficients are divided by the square root of that variance, floored
at `(1/65535)²` for finite ADC arithmetic, then bilinearly interpolated at the
actual integer centers. This includes a shorter final interval when necessary.
Native CFA phase offsets use FP64 frequencies. Each peak supplies the same ten
channels as V178: four asinh real/imaginary transported waves, two `log1p`
powers, two bounded signed cross components, and two frequency coordinates
times continuous power strength. Two directions × four peaks give 80 maps.
The existing zero, bias-free projection adds them to 39 matching coordinates.
There is no hard support cutoff or direct sinusoid-to-RGB correction.

Feature measurement has no gradient; the adapter and matching network retain
gradient flow. Local RAW/RGB coordinates, physical noise output units, frozen
component and zero-variance bypass remain inherited. Constant RAW gives zero
new evidence maps. That property does not guarantee clean RGB for noisy flats.

## CPU evidence

**112 focused CPU tests pass**, including the 24 new tests and 88 existing
projection, global-evidence, local-noise and phase-selection checks. New checks
cover all four Bayer layouts in FP32/FP64, mixed layouts, rectangles, different
bins per batch member, exact grid centers and the shorter final interpolation
interval. All feature channels and center powers agree with independent NumPy
calculations. Test-double forwards check zero-adapter parity, gradients and
ADC/mixed-zero behavior; these are not actual matching-network admissions.

The first run had 23 passes and one test failure: differently grouped off-grid
rational interpolation formulas differed by rounding. Its source and log are
preserved. The corrected off-grid expectation allows 4e−15 absolute error;
grid-center equality and feature/projection tolerances are unchanged. The
neural implementation did not change in response to that failure.

The frozen CPU profile completes six cached cases, using only RAW/variance/CFA
arrays. It makes 12 Torch feature calls covering 36 images, and checks 18
independent NumPy image calculations: **85,196,800 FP64 map values and 21,152
local center powers**. All selected bins match the earlier independently
verified V178 bins; FP32 feature bits equal the FP64 output cast in every case.
Fixed comparison tolerances are 1e−8 absolute and relative.

| Cached case | Feature tensor | Center grid | FP32-input seconds | FP64-input seconds | Maximum map error |
|---|---|---|---:|---:|---:|
| Training mesh, step 1 | 4×80×256×256 | 9×9 | 0.5570 | 0.6354 | 1.76e−13 |
| Training photo, step 2 | 4×80×128×128 | 5×5 | 0.0973 | 0.1050 | 1.01e−13 |
| Training mixed, step 4 | 4×80×256×256 | 9×9 | 0.5493 | 0.5597 | 2.98e−13 |
| Training flat, step 8 | 4×80×256×256 | 9×9 | 0.7428 | 0.5853 | 3.15e−13 |
| Main GFX overcast sky | 1×80×256×256 | 9×9 | 0.1215 | 0.1172 | 2.14e−13 |
| Fine green cab mesh | 1×80×384×384 | 13×13 | 0.2664 | 0.2873 | 1.05e−12 |

Maximum center-power error is 1.28e−13. These are single CPU feature-call times
on CPUs 6/7 at nice 10; local moments use FP64 for either input dtype. They are
not CUDA or model throughput. Peak process RSS is **1,349.67 MiB**; the largest
FP32 feature tensor is 80 MiB. The process leaves RNG unchanged and never
initializes CUDA.

One CPU checkpoint load verifies both raw/EMA initializations from V172 step
1000, SHA256 `d56becdb999f29860e30ac8c89c873958bc3c82f750e855f21cb9864b10b3869`.
Each retains 188 old tensors and adds one zero tensor. Their tensor-only hashes
equal V178's corresponding zero-adapter states: identical tensors do **not**
identify the differing feature operator. Any later checkpoint must record
`LateLocalPhaseEvidenceMatchingDetail`, configuration and source alongside its
weights. New-variant Adam restoration has not been tested here.

## Remaining decisions

Interpolating normalized complex coefficients changes their marginal variance
and correlation. Interpolated powers are features, not calibrated SNR or false
discovery probabilities. Finite windows and interpolation spread support;
halos, broad structure, grid seams, global peak mistakes, weak unknown
frequencies and native aliases remain possible. The local window, nuisance
fit, aggregation and interpolation change together, so equal parameter counts
alone do not isolate a single cause. FP64 moments are a reference implementation;
the limited CUDA probe timings above do not establish full-frame cost.

Actual CUDA feature parity, full-network zero-adapter parity/gradients and
genuine optimizer restoration now pass, followed by the completed continuation
and native restored comparison above. V175 and V178's
completed comparisons retain their existing recipes and source snapshots.

Both protected GFX families appear here only as cached input geometry, without
reference decoding or RGB restoration. Originals and `/mnt/dataz` are unused;
the captures, JPEGs and siblings remain excluded from training. Future quality
reports must retain main-scene sky/building/foliage/fence and the fine cab mesh,
plus at least two native noisy/restored/exact constructed-GT triplets. ISO100,
independently demosaiced and JPEG references remain qualitative references.
For completed restored comparisons use [V172](local-noise-matching.md),
[V174](spread-sample-matching.md) and the stronger-detail
[V161](harmonic-frequency-context.md), including their quiet/flat costs.
