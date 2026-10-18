# Test RAW feature coordinates from identical fresh models

Started a CPU-only mechanism test while the original DINO continuation runs.
The earlier RAW gain4 experiment preserved internal feature values by dividing
stem columns and transforming Adam moments. It therefore did not test a fresh
initialization with stronger RAW features relative to constant conditioning.
The new three arms use raw inputs, uncompensated RAW featuregain32 and a fixed
known-shot/read pointwise compander. All have the same fresh seed51 parameter
bytes and a common zero-head bilinear initial function. No production model,
training recipe or source selection is changed.

The compander preserves sensor0/1 endpoints, retains negative measurements
through linear continuation, and remains monotonic with a positive smooth
join derivative. It is exactly identity when shot is zero. Its coefficients
come from the supplied shot/read parameters, without computing crop statistics.
Only the four RAW feature slots change. Original variance/CFA/WB/matrix fields,
physical signal skip and camera-RGB output/loss units stay fixed. No inverse
transform or extra trainable parameter is added. This tests representations,
including noise-aware preconditioning, rather than proving a universal scaling
explanation for weak learning.

Seven math/actual-trunk CPU tests passed in3.75s; Ruff passes. They cover signed
inputs,16-bit increments, fixed endpoints, zero-shot identity, crop/batch
independence, finite positive gradients, outer AMP FP32, all four CFA initial
signals and restoration of the isolated feature hook after exceptions.

The worker uses the existing16 production training batches8001-8016:
64 retained examples,7 Commons/procedural,4 native synthetic,5 paired. Same
actual noisy arrays/fingerprints, targets, calibration,256px/B4 and original
losses. All models/AdamW states start fresh, without parent/EMA/Gaussian/timing
weights. LR2e-4/decay.01/clip1 are common;256 planned updates repeat the16
observations16 times without a production warmup or schedule claim. Whole-set
training losses/MSE are measured at0/64/128/256, with paired MSE restricted to
valid measured reference-CFA samples. These errors are not generalization or
convergence evidence. Learned states are discarded and cannot initialize a
quality run.

Actual initialization checks have completed all16 forwards for each arm and
verify identical bilinear outputs. Common model tensor digest:
ed1fdca69f4568ffc4c687db6f6677703c8f1b8203353975dd56476f74cc378d;
common Torch RNG digest:
9e2d4112a0b8384c304c4c7a38b5b2c11ddadd7b1d88a68b1920c4c6abed80c0.
The first16 actual updates per arm are retained as48 audited rows. All three
arms use matching production-step/domain order, with finite losses and gradient
norms. The frozen worker emits a PyTorch scalar-logging warning once after
backward; it is still running normally and no source is changed mid-execution.
A transient syntax error in a monitoring command was corrected by re-polling
the same live process; the experiment was not restarted.

Exact live worker PID2012360/create-time1792282156.8, CUDA hidden, Torch2 CPU
compute threads/interop1. At the first-cycle poll its CPU time advanced and RSS
was about1.25GiB; CPU backward is substantially slower than forward, so only
the measured completed prefix is reported. Once original training exits, the
worker yields before forwards/updates until all exact owned review/timing
controllers and final children exit. It introduces no GPU work or owned CPU
competition during those measurements. All original GPU pipeline owners remain
live. Their quality/speed decisions and the full PROMPT.md goal are still open.

Plan SHA ca3fc1f8bc18bd567b189f642b25e376fcb03695869fcec743438726000254ca,
42 frozen guards/19 inputs. Private root:
/mnt/external/demosaic/benchmarks/packed-isotropic-fresh-coordinate-CPU-v1/.
Live status: /mnt/external/demosaic/runs/packed-isotropic-fresh-coordinate-CPU-v1.json.
Public note: docs/packed-isotropic-fresh-coordinates.md.
Public launch receipt: docs/results/packed-isotropic-fresh-coordinate-CPU-launch-v1.json.
Public receipt SHA 00c69011e31367ea483972a64eb867214ad71a80b513ee9e792937fcb889e07e.
