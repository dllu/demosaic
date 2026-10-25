# More paired scenes with the original camera proportions

The reviewed83-ID paired extension adds scene diversity but changes the
scene-group camera mix: Sony becomes60/71 groups, versus24/32 originally.
The optional `paired_camera_sampling_weights` setting keeps a declared camera
distribution while choosing scene groups uniformly within each camera. Cases,
exposures and crops are then sampled within the chosen group. Defaults retain
the original uniform scene-group sampler and its exact RNG sequence.

A separate derived83-ID/71-group manifest now includes the four corrected
train32 masks. All102 new reviewed cases and their crops retain their original
records and bytes; the canonical admission payload is unchanged. This is
prepared data, without a trained-quality claim or a change to current models.
[Data/reader/source receipts](results/paired83-camera-mask-reader-v1.json) ·
[Original review](paired-training-admission.md) ·
[Reference-mask rationale](paired-reference-quality.md).

| Camera metadata label | Original32 groups | Expanded71 groups | Preserved probability |
| --- | ---: | ---: | ---: |
| `ILCE-7C` | 24 | 60 | 75% |
| `Canon EOS 6D` | 4 | 7 | 12.5% |
| `NIKON Z 6` | 3 | 3 | 9.375% |
| `NIKON D40` | 1 | 1 | 3.125% |

```yaml
paired_camera_sampling_weights:
  ILCE-7C: 0.75
  Canon EOS 6D: 0.125
  NIKON Z 6: 0.09375
  NIKON D40: 0.03125
```

These probabilities preserve the old camera marginal, rather than giving the
camera with most newly added views still more weight. They do not preserve the
old per-image draws or the exposure/content distribution within a camera, and
do not prove that the expanded data improves restoration. The older V53/V54
comparison used a different architecture and uniform71-group sampling; it is
not a measurement of this recipe.

## Actual data and restart checks

The derived manifest contains83 publisher IDs/71 sampling groups/166 cases/
1492 cached crops. Its SHA256 is
`7f7ac15b8d285fb140dea9fb5ec4b24b3385f51d901b51a12fd17e89e3fb70ac`.
Path:
`.cache/current-quality-20261023-v1/paired83-mask-camera-preflight-v1/dataset/manifest.json`.
It is built from the exact registered51-ID admission and the existing corrected
train32 manifest, with no source RAW decode, newly admitted case or changed
protected split. The standing GFX scene and protected cases remain excluded.

Actual native256 reads cover every one of the71 groups and all four revised
caches:76 samples with54,789,464 finite tensor values. The default reader
matches the frozen pre-feature reader exactly for11 indices, covering all four
cameras and revised caches:7,930,054 tensor values. That comparison reuses the
same validated constructor fields and executes the frozen original reader;
it does not rehash the old dataset through another constructor.

A metadata-only seed65/20k/B16 schedule contains5021 paired,4966 native and
10013 Commons batches. Its80,336 paired draws give60,276 Sony /9966 Canon /
7481 Z6 /2613 D40 examples, close to the declared probabilities. This verifies
the source-selection schedule, not all unlogged production tensors.

The93 focused tests include actual sampled camera/group frequencies, index
determinism, global-RNG preservation, invalid/missing weights, camera-consistent
groups, admission/legacy behavior and exact CPU toy-training interruption/
restart. Removing camera weighting on resume is rejected. Weights require
paired training, positive finite values and exact coverage of dataset cameras;
configuration and checkpoint snapshots retain canonical probabilities.

Actual data preparation imports Torch only for dataset tensors, forbids all
neural Module calls, leaves CUDA uninitialized and preserves global Python/Torch
RNG. It adds no model inference, optimizer updates, noise draws or RAW decodes.
The source files, original manifests, reviewed crops and prior receipts remain
preserved. Quality must be measured in the subsequent complete model review.
