# Retained predictions for quality reports

**The matched V114/V115 endpoint evaluation is queued after training.** It
evaluates each new model once per declared observation and retains the native
FP32 predictions and exact supervision used by the evaluator. This supports
independent score checks, crop reports and later diagnostics without repeating
model inference. The trained endpoints and their quality results remain pending.

[Queue, source boundary, genuine-output replay and test evidence](results/v112-prediction-archive-evaluation-queued-v1.json) ·
[Current guarded training/evaluation queues](results/v112-spawn-guard-training-and-evaluation-v2.json) ·
[Matched training](small-aligned-training.md).

The initial queue stopped after its training dependency's pre-forward spawn
failure. Its replacement waits for the guarded training controller; both actual
CUDA checks pass and V114 production is running. The failed attempt performed
zero learned work. Original sources/receipts remain preserved.

## Scheduled coverage

| Stage | Observations per model | Model/encoder calls per model |
| --- | ---: | ---: |
| 427 photos + 16 procedural sources, seven conditions/four CFAs | 12,404 | 3,108 |
| Known cameras | 72 | 24 |
| Unseen cameras | 90 | 30 |
| Weak carriers and neutral flats | 448 | 112 |
| Analytic colors | 1,176 | 1,176 |
| Four standing GFX contexts | 4 | 4 |
| Two GFX highlight contexts | 2 | 2 |
| Complete GFX frame, 520 tiles | 520 tile observations | 130 |

Both models together require 9,172 new model/encoder calls. These are ordinary
single-view FP32 comparisons; eight-view inference is a separate policy.
The existing V112 and stronger RawNIND measurements remain controls and are
not rerun. Explicit per-checkpoint lineage distinguishes the V112 Tiny parent
from the training-only fitted Small initializer.

The controller waits for the exact matched-training PID/creation time, successful
terminal state and all four CUDA/training receipts. Checkpoints are frozen from
the completed, verified files. Every numerical-panel input batch must match the
original completed eight-view input witness, and both new methods must receive
identical observations and supervision. The photo observation function is
AST-identical to the original. It is not regenerated twice for that check.

Evaluation source changes are limited to optional callbacks in the photo and
camera evaluators, the new archive, and evaluation helpers. The physical model
and training data modules match the actual frozen training sources. Training
plans, sources, budgets and original GPU owners remain untouched. The mutable
current-model recommendation is not pinned by this queue.

## What is retained

The [archive](../src/demosaic/prediction_archive.py) stores each numerical-panel
prediction as native B×3×H×W float32, including signed and above-white values.
It performs no clipping, quantization, resizing or display conversion. Exact
targets/reference tensors, WB and camera matrices are stored in shared,
content-addressed supervision files. Prepared cameras also retain the measured
reference and validity mask. Their AHD reference remains auxiliary, not exact GT.

Records include checkpoint hash, inference policy, source/draw IDs, conditions,
input fingerprints, array shapes/dtypes and file/value hashes. Cross-method
alignment rejects changed sources, ordering, inputs or supervision. Existing
color-grid predictions are hard-linked into the archive rather than written a
second time; the evaluator's already loaded observations supply supervision.

Actual packed input/colors are also retained for the selected material sources,
so native noisy/denoised/exact synthetic GT triplets can be built later without
generating noise again. Color cases retain these fields for CFA diagnostics.
The GFX reporter already saves full context predictions. Complete-frame runs
add six unquantized native ROI arrays per model before RGB16 encoding, alongside
linear/sRGB16 TIFFs. The complete full-frame FP32 arrays are not retained.

An archive can be read without CUDA or a model:

```python
from demosaic.prediction_archive import iter_predictions

for row, prediction, supervision in iter_predictions("/path/to/archive/records.jsonl"):
    print(row["model"]["label"], row["context"]["ids"], prediction.shape)
```

The reader checks file hashes and logical array metadata before yielding values.
Existing archive directories and duplicate observations are rejected. A failure
keeps completed records and partial evidence and stops without automatic retry.

## Verification and resource boundary

Thirty-eight targeted tests pass, covering signed/HDR FP32 fidelity, supervision
sharing, source/input/order mismatches, corruption, inference-policy separation,
existing-file sharing, and evaluator callbacks. Nonlearned operator fixtures
confirm that callbacks add no model evaluations and receive actual targets/masks.

A separate proof replays four already-retained genuine Tiny/Small predictions
on two difficult camera cases. All four native predictions remain bit-exact,
both models share the two supervision files, and independently reconstructed
sensor PSNR matches exactly. The proof imports no Torch, runs no model and
decodes no RAW. This verifies retention; it does not measure new model quality.

The frozen queue budgets about 30GiB for retained data, shared weights and
exports. It requires 248GiB free external space before the first stage, 216GiB
before later stages and a 208GiB runtime reserve, with 48GiB available RAM at
stage start and a 24GiB CUDA allocation quota. These are new prospective limits
after training exits; earlier frozen workflow limits are unchanged.

Full metric reconstruction and actual native viewing follow the completed
endpoints. Reports must include at least two native triplets and the standing
GFX foliage/fence and other regions, with accurate reference labels. Useful
measured gains can advance the docs and implementation without a historical
promotion gate freezing the model choice.
