# IEEE training and flat learnability controls

Added explicit training `precision: float32`, guarding forward/loss and backward
against TF32. Validation uses the selected neural precision. BF16 remains the
legacy default; precision changes are rejected on resume. A new test instruments
both forward/backward and verifies guard restoration and resume rejection.
The complete 150-test suite and Ruff pass.

Launched matched 1000-step V12 BF16 / V13 IEEE-FP32 controls, from the same frozen
V11 step5000 EMA. They use only continuous-precision smooth scenes, original loss,
same seed/noise/camera distribution/schedule, LR1e-4 and 250-step checkpoints.
Four photographic monitor sources are used only as a diagnostic. No recipe is
promoted from these trials; full-photo and real comparisons remain required.

The experiment distinguishes denoising learnability under an unambiguous flat
target from the broader photographic curriculum, and tests whether weak RAW
variations are obscured by BF16 features with larger metadata offsets. This is a
hypothesis, not an established explanation. Both CUDA runs have finite losses;
FP32 peak CUDA allocation is ~2.94 GB, within shared-memory limits. No other
user's processes were modified.
