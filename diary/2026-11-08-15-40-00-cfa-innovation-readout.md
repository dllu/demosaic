# Ground innovation corrections in all CFA colors

Recorded: 2026-11-08T15:40:00-08:00 (America/Los_Angeles).

Published the completed V197 comparison and all evidence in commit `f1cdb983`.
The innovation head gives clearly stronger periodic mesh modulation but also a
pronounced red/cyan building artifact and extra flat/photographic waves. The
native cab and building triplets were inspected again before choosing this
follow-up. V195/V187 retain useful lower-error strengths; no general promotion.

V197's two green measurements can be mixed freely into RGB. This permits
unsupported color correction, but does not establish the cause of the observed
artifact. Implemented V198 as a combined representation change above the good
V195 Whole EMA anchor: all four actual CFA phases, affine-plus-wave real least
squares in physical camera units, canonical red/mean-green/blue synthesis,
24->16->3 real tanh gates and summed modes. Gains may invert sign but cannot
learn arbitrary quadrature rotation. Red/blue cannot synthesize from green's
wave. The numerical rank cutoff and nominal RAW noise units are not confidence;
noisy own-color waves, edge leakage and false texture remain possible.

Only four new tensors / 451 parameters train; all 193 inherited trained tensors
are frozen. The old 104 neural source files are unchanged. The new 105th file
does not extend the bad V197 head. Additional channels, least-squares units,
signed bounded gains, summation and capacity change together; do not claim a
color-grounding-only causal ablation. The source shorthand about unrotated
phase and trace-variance normalization is clarified in the public design note:
sign inversion is possible, and nominal coefficients divide by square-root
trace variance. The frozen execution source bytes remain intact.

All 23 new CPU tests pass against independent NumPy least squares/interpolation,
known native waves for four Bayer layouts and both FP32/FP64, color-zero and
bound identities, singular Nyquist rank, mixed layouts, affine rejection,
isolated learning, strict state and ADC routing. Broader old/new wave regression
passes 85 tests. Ruff passes.

Actual admission owner PID1833259/create1794181561.82 completed eight bit-exact
trained-anchor parities, seven CPU/GPU large/small feature and nonzero-head
comparisons, two training-only updates with independent CPU gradients and one
actual full model/Adam/EMA/CPU-CUDA RNG restore. The protected sky, cab and
building were parity-only, with no gradients. Four strict CPU raw/EMA loads of
the two factored probe checkpoints compare 772 frozen-anchor tensors. Probe
states are never full-training initializers. Admission peak CUDA allocation of
6.233 GiB is not a 100MP benchmark. No neural prediction prefix was repeated.

Launched a fresh 1000-row/900-update run with seed 202611080198, the same cached
observations/pair units, V195 Whole ten-term objective, clean masks, LR/WD/clip
and 100 ADC skips. It preserves the anchor's separate V187 900 + V195 900 history.
Controller PID1834894/create1794181646.79 and worker PID1834895/create1794181646.86
were live at the launch inspection. Row-eight full-state restoration succeeded
and continued at row nine; no prefix replay. The controller will run the frozen
full CPU trace/checkpoint audit once the registered worker is terminal. Later
status/terminal receipts remain authoritative.

Both raw/EMA endpoints still require all 822 cases and native comparisons,
including exact-GT mesh/flat/photo controls and both GFX qualitative scenes,
building, sky, foliage, coarse fence, both fine-cab ROIs and noise profiles.
No image-quality improvement or artifact fix is claimed from engineering tests
or training loss. Keep real references labeled independent and non-exact.

Total trial output budget is 2 GiB local, above a 40 GiB reserve; no external writes,
new data/noise/parent predictions/RAW decode, original access or unavailable
dataz access. Existing arrays are read in place and checkpoints bind 193 frozen
anchor tensors. Prior machine receipts and experiment bytes are preserved.

[Design and required comparison](../docs/cfa-innovation-wave.md) ·
[Preparation and launch evidence](../docs/results/v198-cfa-innovation-prepared-v1.json).
