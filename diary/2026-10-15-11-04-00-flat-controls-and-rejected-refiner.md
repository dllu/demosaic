# Flat controls and rejected refiner

V12/V13 completed 1000 matched flat-only steps. IEEE FP32 evaluation gives
retained sigma fractions .18519/.17141/.16988 for BF16 training and
.18232/.17149/.17062 for IEEE FP32. The precision explanation is not supported
as the dominant cause in this recipe. Reports freeze the actual final weights;
no moving-checkpoint ambiguity.

Implemented the optional zero-initialized RGB noise refiner (27,696 parameters)
and refiner-only training, with explicit IEEE FP32 arithmetic and noise-scaled
output. V14 trained only this branch for 1000 steps, base/DINO frozen, all flat
targets and original loss, learning rate 5e-4. Tests verify exact identity at
initialization, zero correction at zero variance, a representable flat averaging
solution, proper gradients and FP32 behavior inside CUDA BF16 autocast.

Flat fractions improve to .06116/.05187/.06681, but the four-scene real RAW
measured PSNR drops to 48.46935 and auxiliary PSNR to 35.85693 versus V11's
51.69319/37.66384. Native crop triplets expose smoothing of genuine structure and
edge phase patterns. RawNIND remains 54.06860/39.67805. Rejected for promotion;
neither this architecture setting nor its weights become a new default. The
trial also appears alongside V11/RawNIND in the cached GFX qualitative report.

Added docs/refinement-review.md with two native noisy/V14/reference triplets,
accurate auxiliary-reference labels, dataset credits and a complete diagnostic
receipt. Probe now archives source and explicitly evaluates RawNIND in IEEE
FP32. Full suite 155 passed, Ruff clean. Training jobs are terminal. No official
test selection, no source-photo writes, and the project quality goal remains open.
