# Broad camera and shadow-loss controls

The M100 development failure warrants changing training camera coverage before
changing the architecture. Added opt-in neutral-preserving spectral mixing with
stronger primary overlap, red/blue WB 0.65–3.6, 25% near-identity transforms,
and a determinant guard. It copies no evaluation-camera matrices. A 100000-draw
diagnostic found finite matrices, minimum determinant 0.0800 and maximum condition
number 9.95. Round-trip and neutral-response tests pass.

V7 initializes the frozen V6 step51000 EMA and retains every head and architecture
parameter. The only recipe change is camera augmentation. It is scheduled for
10000 steps with a review stop at 5000, LR 5e-5, original seed42/data/losses.
The original V6 100000-step job continues as a control. Source snapshots and
initialization receipts preserve the actual code and checkpoint hash.

Prepared a matched V8 control with an additional 0.02 noise-normalized observed-CFA
loss. Variance comes from clean target and known shot/read coefficients; its
standard-deviation floor is 1e-4. Exclude ADC-only draws and reconstructed/clipped
highlights, retaining their original losses. Tests check equal-noise-unit errors,
relative shadow gradients, exclusions, the disabled legacy path and exact CPU
restart equivalence with the new recipe. All 106 tests passed before the additional
restart case; the targeted ten-test camera/loss/restart suite also passes.

V7 has begun with finite losses. V8 has no quality evidence yet and is not a
promoted configuration. A full 427-photo + 16-stress V6 step51000 comparison against
the corrected signed-input IEEE-FP32 RawNIND baseline is also running. The final
test partitions remain untouched.
