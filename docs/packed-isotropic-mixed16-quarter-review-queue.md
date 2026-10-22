# Queued mixed16 review at160,000 examples

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

The [complete review](packed-isotropic-mixed16-quarter-review.md) finished after both
[continuations finished](packed-isotropic-mixed16-quarter-training.md) at10k /
160,000 examples and their exact owners exited. The independent full-state,
source and schedule boundary gate passed; the first stage was known-camera
evaluation. Known/unseen, full427, analytic and full-frame GFX reports have now
closed. The [GFX native inspection](results/mixed16-quarter-GFX-native-view-v1.json)
adds24 actually viewed triplets at the four standing regions. The
[three-camera native inspection](results/mixed16-quarter-three-camera-native-view-v1.json)
adds another24 triplets from six cached contexts. The
[selected-color inspection](results/mixed16-quarter-selected-colors-native-view-v1.json)
covers16 original/additional analytic triplets. All4,704 fresh FP32 hue
predictions, supplementary highlights, statistical/artifact checks and parent
progress comparisons have completed. All146 triplets/202 native cells were
actually inspected and matched to final reports; the owner exited successfully.
Neither checkpoint is promoted. The original decision kept V43 as its reference
and selects CUDA profile/EMA analysis before the next training budget.
The requirements below describe the preserved execution plan.

[Frozen plan, exact owners, executed sources and CPU preflight](results/packed-isotropic-mixed16-quarter-review-queue-v1.json).
Live status:
`/mnt/external/demosaic/runs/packed-isotropic-mixed16-quarter-review-workflow-v1.json`.

After the training controller exits, the reviewer requires both successful
10k optimizer /40k data-step /160k-example endpoints and final child exit.
It independently checks finite model/EMA/Adam states, original source bundle,
data/precision/units/LR/horizon, actual CUDA restoration receipts and the next
16 original input batches. All403 logged source/noise/LR/example records must
match across the pair and403 overlapping older RAW observations per arm.
An incomplete or failed training status stops the review before inference.

The fixed review includes:

- Fresh FP32 known/unseen-camera and full427-photo/16-procedural panels:
  six neural methods, two RawNIND adapters and three classical methods.
  V72/V73 are compared with mature V43/V63 and older V71/V70 at the same
  160,000-example budget. Those older models differ in units, precision,
  optimizer grouping and EMA; this comparison cannot isolate the batch effect.
- Separate progress comparisons against each preserved32k-example parent.
  Existing parent scores are reused after matching protocol, observation
  coverage and classical-control witnesses. This avoids repeating parent
  inference. Six comparisons produce24 source-balanced metric differences.
- Analytic detail, three cached cameras, selected colors,4,704 fresh FP32
  hue predictions, supplementary GFX sign/platform contexts, independent
  arithmetic/artifact checks and117 fixed-cohort sensitivities.
- Full GFX restores with twelve RGB16 exports and native sky, building,
  foliage and fence triplets. Display coordinates/transforms stay fixed;
  the separate ISO100 image is a qualitative reference, never exact GT.

The CPU integration preflight rejects the actual running training job. It then
aliases the completed parent reports against themselves: all24 differences and
bootstrap intervals are exactly zero, with six matched classical witnesses.
It performs no inference and initializes no CUDA context. Targeted review,
boundary and source-sensitivity checks pass63 tests; Ruff passes.

The queue reuses the frozen serial review runner with the new boundary operator.
It adds an independent analytic summary audit and separate parent progression
before its final terminal status. It stops on failure without an automatic
restart, training extension or promotion. Actual unresized crop inspection and
the final quality decision were completed separately. Shared-machine full-frame
times are descriptive observations. Protected-final scenes remain closed.
