# Diagnose the saved original20k control regression

The preceding goal turn was a verified wait: actual expanded trainer
PID169989/creation1792243965.62 and both review owners were live. At15:44:57UTC
the same trainer reached step16975 of its original20000 schedule, with no
recipe, source, checkpoint or queue changes. The full objective remains unmet.

Added `scripts/decompose_control_errors.py` and executed it against the unchanged
completed control endpoint receipt, SHA256
`e85c149629c4f7fef7b0e66e81d2a4ef5fafce8d72c0d588ab29c0987abdd24d`.
The analysis verifies checkpoint, prediction, observation-plan and target hashes.
There are no model imports, new neural forwards, training, original-file reads,
noise draws or corrections. Existing actual4k/20k F32 outputs and exact simulated
targets suffice. Real-camera references are excluded from these measurements.

Four previously selected targets ×two endpoints ×two spaces ×two regions give
32 additive MSE decompositions. Independent scalar `math.fsum` moments and nested
block-average energy differences check the Haar coefficient results, including
band assignments, with maximum discrepancy2.7755575615628914e−17 at fixed1e−14
tolerance. Nine mathematical/geometry tests pass; Ruff passes. The four original
photographic triplets were actually reopened at native100%, and their hashes,
dimensions and metadata are retained in the publication receipt.

On the fabric photo's border8 context,88.36% of added unclipped camera-RGB MSE
is increased mean bias and10.53% is coarse residual error after four Haar
reductions. The corresponding sRGB fractions are86.48% and12.62%. The finest
two bands improve slightly. Magenta's large total-error improvement hides a
70.05% increase in zero-mean camera-RGB MSE. Neither observation establishes a
cause, restoration-noise power, true texture recovery or an effective correction.
This changes the follow-up interpretation: the fabric PSNR regression alone
does not support increased finest-scale smoothing. The already prepared
normalization augmentation has a concrete color/coarse failure to test, after
the existing original20k reviews. No model is promoted and no extra job is queued.

Artifacts:

- `/mnt/external/demosaic/benchmarks/control-original20k-error-decomposition-v1/`
  contains the frozen executed operator, result, native review and publication
  binding. Analysis SHA256
  `b7fcfc340229db9f33eb42abee449c535d6e50af2c8fb7c4dd0926fa2562e762`.
- `docs/control-original20k-error-decomposition.md` and its public JSON receipt
  explain the diagnosis and reuse four original noisy/model/exact-GT triplets.
- The original control report and normalization preparation link the diagnosis.

The original427 two-arm evaluation, final hue/artifact review and the fixed
418/416 source sensitivities still await the actual expanded endpoint. Preserve
the active owners and all original data/operator bindings. The10s/100MP and
strong real-photo-quality objectives remain unmet/unproven.
