# Fixed local RAW contrast: discarded CUDA diagnostic

Local mean subtraction slightly improves native/paired original loss over input
gain32 at common small residual units, but weakens Commons loss/MSE and native
MSE. No single arm wins across all domain losses and MSE. No production setting
or trained model is adopted. [Numerical evidence](results/packed-isotropic-local-contrast-CUDA-v1.json)
contains the full curves and independent replay.

All four fresh models share seed51, identical3,464,396 initial parameters,
852 tensors, and exactly identical initial bilinear predictions on all16
fixtures. All learned residuals use a common1/32 multiplier; the physical RAW
skip and output/loss units stay fixed. Only the four neural RAW features change:
original RAW, RAW×32, or32×(RAW−local mean) with a reflected7/31-pixel mean
within each packed CFA phase. Other28 variance/CFA/WB/matrix features remain
identical. Filtering removes DC from those four features; the physical signal
still bypasses the network. It adds local context dependence, without adaptive
scaling, image-wide normalization, interpolation or new parameters.

The same16 training-only B4 observations repeat16 times:256 updates at
constant LR2e−4, AdamW decay.01, clipping1, CUDA IEEE FP32 NCHW without AMP
or TF32. Sources, noise, ordering and original domain losses match the
[preceding residual-unit test](packed-isotropic-residual-units.md). Learned
weights are discarded; GFX, validation and protected-final scenes are unused.

Ratios at256 updates to the common initial values, **loss / MSE**, lower better:

| RAW features, all residual÷32 | Commons/procedural | Native-clean | Paired |
| --- | --- | --- | --- |
| Original | 1.00075 / .98899 | 1.00506 / .99779 | 1.00219 / 1.00222 |
| Gain32 | .97616 / .93474 | .99937 / .99575 | .99582 / 1.00109 |
| Local7 ×32 | .99498 / .99003 | .97714 / .99846 | .99286 / .99693 |
| Local31 ×32 | .99535 / .99287 | .98314 / .99784 | .99363 / .99511 |

These are small fixed-training-set effects. Paired MSE uses only valid measured
reference-CFA samples, not exact RGB GT. The duplicate gain32 control closely
tracks the preceding GPU experiment; no bitwise training-repeat claim is made.
Neither generalization nor convergence is established.

Eight tests check the reflected phase filters against a direct calculation,
locality,16-bit changes, FP32 under outer autocast, all-CFA physical signal and
unchanged metadata/state/parameter identities, hook cleanup and invalid modes.
Independent replay verifies1024 ordered finite training rows,96 domain mean
reductions,33 inputs and46 guards. All852 Adam states per arm are finite at256,
all fixture fingerprints stay unchanged, and the exact GPU process has exited.
