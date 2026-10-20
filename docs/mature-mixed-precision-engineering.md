# Mature mixed-precision engineering and serial pilot

The [completed precision pilot](mature-mixed-precision-pilot-review.md) passes
the fixed CUDA/native/numerical screen on both mature checkpoints. Hidden
FP16 resident B4/native512 medians are162.49/173.51ms, versus690.54/704.41ms
FP32:4.250×/4.060× observed ratios. All48 native cells and independent Torch
arithmetic checks complete. Full quality and actual100MP qualification remain.
The [mature full-frame result](mature-cudnn-fullframe.md) remains118.22/120.48s
warmed IEEE FP32. Older V42 FP16 timings use different V37 weights.

| Policy | Neural autocast | First hidden encoder | Physical head/native skip/tail/inverse |
| --- | --- | --- | --- |
| `fp32` | IEEE FP32 | FP32 | original FP32 |
| `fp16` | FP16 | original FP32 residual input | original FP32 |
| `fp16-hidden` | FP16 | existing FP16 hidden branch | original FP32 |

Weights, checkpoint/config values and production defaults remain unchanged.
The scoped research override restores the hidden flag even on exceptions.
Explicit CPU half is engineering emulation; the production CPU API remains
FP32. V43 uses its actual DINOv3 ViT-S and V63 its actual ConvNeXt-Tiny. This
does not qualify V92's new head for half precision.

## Actual CPU evidence

The [CPU receipt](results/mature-mixed-precision-CPU-v1.json) records76 actual
forwards:12 native64×80 measurements per policy/model, plus one explicit-FP32
hidden-flag identity and one repeated-half control per model. Inputs cover
four CFAs, ADC/highest-noise conditions and an exact one-DN ADC perturbation.
Targets never enter forwards. Outputs are finite FP32; head/tail/middle and
first-encoder dtypes follow the intended policy. Each actual forward invokes
the frozen DINO once. Both extra controls are exact on the first ADC fixture.

Every model/config/state/parameter identity, input, checkpoint and Python/Torch
RNG check passes; CUDA is never initialized. All24 policy/CFA ramp outputs
retain more than256 quantized codes: minimum8,669 for V43 and8,620 for V63.
Every one-DN response is nonzero; the smallest RMS is1.52298e-5 camera RGB.
This verifies sensitivity in small engineering inputs. Faithful reconstruction,
CUDA accuracy and photographic behavior remain unqualified.

The [independent NumPy audit](results/mature-mixed-precision-engineering-v1.json)
reopens all72 saved arrays, verifies hashes/shapes/finiteness, and recomputes
24 code counts plus24 one-DN RMS fields. All48 scalars agree exactly. Encoder
hashes remain `35035ba142eb119cd5980cf0d9809bfa28f622538c259ffb0fcf348ca6e68898`
(V43) and `370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`
(V63).

All18 policy/legacy tests pass, covering ambient BF16, explicit CPU opt-in,
exception restoration, FP32 identity, native ADC sensitivity and incompatible
paths. Seven queue tests reject live predecessors, surviving dynamic children,
incomplete/dead owners, failed stages and changed owner/plan identities.
These25 tests establish execution/ownership contracts, without a CUDA or
full-frame performance claim.

## Frozen CUDA work and ownership

The [CUDA plan](results/mature-mixed-precision-plan-v1.json) freezes29 fixture
batches /110 actual observations: two exact-GT photos, four standing GFX512
contexts, all96 unique existing analytic measurements and eight native ramp/
one-DN observations. All methods use identical complete measurements and
transforms. The existing192 ADC labels represent48 unique deterministic
observations; all12 groups and four CFAs remain.

Controller1331098/create1792508313.33 was separately detached. Its
[launch receipt](results/mature-mixed-precision-queue-v1.json) binds CPU proof
and25 tests. It waits for exact V92 training, review, closure, reference and
native-package owners, including surviving dynamic children. Successful
terminal stages and original owner/plan identities must agree. The recorded
handoff confirms the process actually live, zero children and no GPU output
at launch. After every exact predecessor exited, worker1400254/create1792512940.95
ran once and completed212 forwards /198 arrays. Both pilot owners have exited.
Failed predecessors fail this pilot; it never restarts or stops those jobs.

Only after that barrier and48GiB headroom for60s may its single GPU worker
start. Bounds are16GiB CUDA allocation,24GiB active RAM, root64GiB/external
500GiB reserves and900s runtime, with no automatic retry. Predecessor waiting
is bounded to12h and later resource waiting to1h. Local SSD outputs preserve
external checkpoint space and avoid reading original RAWs. Backend/quota
settings and state/input/RNG invariants must be preserved.

Three excluded GFX warmups precede four synchronized unhooked resident samples
per policy in balanced order reversed between models. First policy calls share
per-process library caches; they are not isolated cold starts or pure search
cost. Save all unquantized outputs. Actual native160px photo/GFX viewing and
independent scalar checks must precede interpreting quality/timing summaries.
The frozen photo triplets, foliage/fence crops and ISO100-reference caveat apply.

Operational files are under `.cache/benchmarks/mature-mixed-precision-CUDA-v1/`;
CPU evidence is under `.cache/benchmarks/mature-mixed-precision-CPU-v1/`.
V92 has completed its [full rejected review](late-rgb-head-only-original4k-review.md).
This finite precision screen selects hidden FP16 for a separately frozen full
quality and100MP study, with no default/export change or automatic continuation.
SOTA, decisive real-photo superiority and actual100MP/10s remain unmet/unproven.

The separate [native/scalar postprocessing](mature-mixed-precision-postprocessing.md)
now passes genuine historical CPU checks:24 original triplet PNGs byte-exact,
36 native board cells,29 independent physical-input fingerprints,576 saved
analytic rows replayed exactly and640 Torch cross-checks within1.29e-14.
Its new scalar reviewer requires actual new-policy native viewing first and
retains per-observation failures alongside group means. This work does not
modify the live GPU plan or supply a new FP16 quality/speed result.
[Complete tool-preflight evidence](results/mature-mixed-precision-postprocessing-v1.json)
binds the61-file prospective postprocessing bundle and11 passing numerical
tests, and records the successful frozen-workspace correction.
