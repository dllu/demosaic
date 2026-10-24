# Fit Small fusion projections while preserving the learned V104 gates

Recorded: 2026-10-24T01:21:39-07:00 (America/Los_Angeles).

Previous turn made progress: the current V104/V111 three-gate intervention
showed both useful fusion and selected color-tail sensitivity. All eight exact
original GPU workflow handles remain live; V112 continues its fixed budget.
The original model-quality/runtime objectives remain open.

Rather than resetting useful gates for every larger encoder, fit Small's four
lateral affine maps to V104 Tiny's lateral outputs on training-only previews.
This changes eight EMA tensors while preserving the other 83, including all
three learned gates, the restoration trunk and official frozen encoders.

Preselected 80 unique sources from the reviewed 90,864-source cohort, disjoint
from validation/test: 64 for fitting and 16 separate training-source checks.
Used the actual clean reader, existing geometry/contrast/downsample recipe and
fixed randomized broad-camera/exposure/noise draws. Every reader call loaded
exactly its bound cache. A real restoration forward verified the manually
constructed normalized preview bit-exactly. Targets for fitting are teacher
features, never held-out restoration GT.

Solved fixed standardized ridge0.001 in float64 with unpenalized intercepts;
installed float32 maps. Known orthogonal systems verify the arithmetic before
neural execution. Feature checks improve at stages0/1/2 but not stage3:
error RMS .16262→.03965, .12052→.03114, 2.92784→.36250 and
.36001→.36748. The deepest-stage limitation remains visible.

The fixed original28 observations compare V104 Tiny, blind Small and fitted
Small, with no held-out tuning. ADC/ISO100/ISO12800 four-photo PSNR means are
39.49290/40.80493/33.49300 for Tiny,
30.59353/35.94253/30.62018 for blind Small, and
39.48010/40.80864/33.49125 after alignment. Six of twelve individual aligned
photo cases improve over Tiny; changes range −.09738 to +.06243dB.
The two adverse-camera PSNRs recover from44.27604/36.72767 to
56.72694/60.41804, still below Tiny56.98928/60.67192.

Actually viewed all112 native cells. Blind transfer causes colored camera
blobs, building/fence distortions and foliage smearing. Alignment largely
restores Tiny appearance. Remaining blotches and fine foliage/sign softness
persist, alongside inherited color bias. Four native photo triplets retain
both candidate variants; the current report includes two aligned examples.
GFX ISO100 and camera AHD remain nonexact references.

Independent Torch64 checks rebuild all four ridge systems/solutions and318
pilot score fields. The actual fitted checkpoint reloads through the public
loader, matches the complete fitted model hash and reproduces both selected
ISO100 photo predictions bit-exactly. Total actual operation is59 restoration
forwards and219 frozen-encoder forwards, including feature collection and two
serialized replays. No CUDA, RAW decoding or joint optimizer updates.

Read-only fitted checkpoint:
`/mnt/external/demosaic/Small-lateral-alignment-CPU-20261024-v1/Small-aligned-from-V104.pt`,
SHA256 `6a055cb6f5e03676c69a9523350e9236b7e19f162b6ca9f535858d14d42e8baa`.
Inherited step20000 refers to V104 history, not a Small joint-training budget.

Preserve this candidate and the earlier unlaunched common-function recipes.
Choose a useful completed parent after V111/V112 full review; a later refit
gets a new immutable plan. Optimizer/CUDA checks and joint training for that
final initializer remain pending. The working V104 selector and original
training/evaluation/export/eight-view queues stay unchanged.

Added the public scripts/fit_dino_laterals.py utility to make the numerical
transfer step reproducible from retained feature pairs. It uses fit records
only, verifies archive hashes and writes coefficients without encoders or
checkpoint mutation. Six focused tests cover analytic ridge shrinkage,
constant channels, invalid regularization and source/check partition boundaries.
Its actual replay reproduces all eight installed float32 coefficient tensors
bit-exactly. Executed public fitter/test bytes are separately preserved.

[Current transfer report and native comparisons](../docs/small-feature-transfer.md) ·
[Source/data/fit/weights/audit/export proof](../docs/results/small-lateral-alignment-CPU-v1.json).

