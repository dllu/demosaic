# Both objective arms complete1k; FP32 review and native GT views started

Previous goal turn was progress: added the backward-compatible optional log-MSE
objective, tested it with real DINO CPU/CUDA preflights and started the matched
cleaned84,867-source trial. This turn completes actual training and moves into
quality evaluation. The full project quality/SOTA and sub10s goals remain open.

Both genuine V63-parent arms exit successfully at1000 of their original4000
updates,16000 new examples each. Independent full-state audit checks91 finite
model/91 EMA/89 AdamW states, all89 model/EMA tensors changed, fixed normalization
buffers, original-horizon LRs, parent/model/data/recipe identities and saved RNG.
All41 logged observation/domain/LR records and first16 actual observations match.
An additional independent replay rebuilds both complete source snapshot digests,
compares every package file and binds training manifests to the frozen input.

Checkpoint SHA256:

- V74 control: be6fd22593420656fc9c4eb93845a80b8731808ee2e20f2655a015c4c0641cee.
- V75 log-MSE: f052ebbbe6bc377653a7f29813cda57132a70b0393ea788e77520c11c1d8d6ea.

Added a frozen review operator gated on exact training controller/final-child
exit. Primary fresh FP32 panels contain two new models plus three classical
controls:360 known-camera,450 unseen-camera and62020 full427/procedural records.
Historical parent/V43/RawNIND gains reuse scores only after exact protocol/keys,
nullable support and existing4-ULP classical witnesses. Source inspection finds13
identical model/data/metric files; all five suite-function and both precision
context ASTs also match. The suite-file difference is checkpoint copying moved
into the verified immutable cache; it does not alter the sampler/NN/metric ASTs.
Torch remains2.14.1+cu130. This does not claim full source byte identity.

Actual historical CPU replay filters completed10k logs to the new five-method
layout and rebuilds108 comparisons/27 exact witnesses, without new inference or
V74/V75 results.24 focused gate/source-sensitivity tests pass in2.76s; Ruff passes.
The first review entrypoint fails before controller claim/inference because
Python-P omits its helper directory. Preserve the exact log/failure receipt;
explicit frozen scripts/src PYTHONPATH fixes the entrypoint with no source,
plan, model, data, precision or gate change. No automatic restart follows failure.

Review plan: .cache/experiments/reconstruction-objective-v74-v75-first1k-review-v1/plan.json
SHA256:9da41bcea0e62226c76fa260ac2ad3c402f84bd567e3fd42c602dd9b8ee2b8a8.
Controller tool session47072. At diary capture, state=running-objective-quality-review, stage=full427;
controller={'pid': 3674819, 'created': 1792337422.79}; last child={'pid': 3676638, 'created': 1792337682.82}.
Recheck actual PIDs/creation times rather than inferring life from this file.
Training and independent boundary stages are complete; known/unseen new inference
has completed and full427 is actively producing real records. Each stage has a
24GiB CUDA allocator cap and an owned one-hour timeout. A direct observed-rate
forecast during full427 was about2073s for the whole phase, below that limit.
No timing result is inferred from this quality review.

Built and actually viewed six fixed photo triplets/ten native160px cells using
four new crops and matching old V63 parent crops, with exact noisy/GT pixel
agreement. All originals and five public PNG copies are byte-bound. Shared
ISO12800 shot.00256/read variance.0000262144, RGGB, WB/matrix, exposure1 and fixed
cache ROIs are recorded. These use the protocol's CUDA seed20261014 noise,
not the other CPU-draw examples. Thin canopy cords/folds and cloud detail remain
missing; no broad gain is claimed. Source crop hashes must be checked again after
the full producer closes. No per-method transform, resampling or fitted correction.

Published [training/native progress](../docs/reconstruction-objective-first1k-review.md),
[boundary](../docs/results/reconstruction-objective-first1k-training-boundary-v1.json)
and [review/native evidence](../docs/results/reconstruction-objective-first1k-review-progress-v1.json).
Top-level representative V43 crops and working model remain unchanged.

Remaining: let the same live full427 worker finish; verify primary comparisons,
predeclared418/416-source sensitivities, analytic fields,3528 fresh hue predictions,
GFX sky/building/foliage/fence contexts and supplementary signs/platform crops.
Recheck all numerical/source receipts, build/view every required native board and
close color arithmetic before deciding on the already-declared continuation
criteria. No automatic training extension, promotion, protected-final scoring or
new full-frame timing. Independent ISO100 GFX reference remains explicitly not GT.
