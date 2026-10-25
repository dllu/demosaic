# Retained predictions for quality reports

**V114/V115 training, endpoint evaluation, independent audit and native review
are complete.** [Results and current model choices](v114-v115-quality.md).
The evaluator
evaluates each new model once per declared observation and retains the native
FP32 predictions and exact supervision used by the evaluator. This supports
independent score checks, crop reports and later diagnostics without repeating
model inference. Both complete102MP exports and all numerical panels are verified.
[Completed training, payload inspection and handoff](results/v114-v115-trained-quality-running-v1.json).

[Queue, source boundary, genuine-output replay and test evidence](results/v112-prediction-archive-evaluation-queued-v1.json) ·
[Guarded training launch](results/v112-spawn-guard-training-and-evaluation-v2.json) ·
[Current corrected evaluation/review queues](results/evaluation-backbone-interface-fix-v1.json) ·
[Matched training](small-aligned-training.md) ·
[Independent audit proof and queue](results/v112-independent-archive-audit-queued-v1.json).

The initial queue stopped after its training dependency's pre-forward spawn
failure. The current evaluator has observed successful exit of the guarded
training controller and completed all eight declared stages. Both actual CUDA checks
and original 20,000-update production runs passed. The failed attempt performed
zero learned work. Original sources/receipts remain preserved.

The current evaluator supplies the required `legacy_sha256` keyword while
checking each checkpoint's explicit official Tiny/Small identity. An interface
review found the omitted keyword before any endpoint evaluation; a regression
test now exercises the real required-keyword interface.
The two idle reviewers were replaced with corrected frozen sources: evaluation
v3 and independent audit v2. Only the collector's execution file changes;
physical model/observations/counts/budgets remain exact to the original queue.
The old idle owners exited without children or completed stages, and their
sources, logs and terminal receipts remain preserved. Original training is now
complete; evaluation and independent audit finished under their original
identities, frozen sources and budgets. The CPU-only direct Tiny/Small join
verified14,190 pairs and prepared the published native material/GFX boards.

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
When an existing prediction and archive are on different filesystems, an
exclusive byte-for-byte copy replaces the hard link. The original stays intact;
other link errors still stop the writer.

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

The original 38-test verification covers signed/HDR FP32 fidelity, supervision
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

## Independent audit after evaluation

The [CPU audit](../scripts/queue_quality_archive_audit.py) now waits for the
exact endpoint-evaluation process to exit successfully with all eight stages.
It then checks **28,380 numerical observations** across the two models, directly
from the saved FP32 predictions and actual targets. It imports no Torch,
regenerates no noise, runs no model and decodes no RAW.

[Independent NumPy64 arithmetic](../src/demosaic/archive_metrics.py) reconstructs
photo linear/rendered PSNR, chroma/gradient error, measured-CFA scores, analytic
color bias, carrier gain/phase/residual and neutral-flat FFT measures. Complete
archive/report joins and shared supervision are required. SSIM and masked
boundary/shadow metrics retain the original evaluator implementation.

Photo comparisons pair the same condition/CFA observations and weight sources
equally. Camera comparisons average crops within capture, captures within scene,
then scenes equally. Source/scene bootstraps describe fixed evaluation units,
not training-seed uncertainty. Existing V112 and stronger RawNIND controls are
reused. Color tails and weak 4/8/16-pixel carriers accompany the primary means.

For each model, the audit also prepares two native 160-pixel triplets of the
preselected bark and canopy sources at ISO12800. Their noisy Malvar, restored
and exact synthetic GT panels use identical ROI, WB/matrix and display exposure.
Receipts record source, checkpoint, conditioning, target/prediction hashes and
encoded cell hashes; every PNG is reopened and checked. Actual viewing of these
and the standing GFX/full-frame foliage/fence regions remains a separate step.
No model recommendation changes automatically.

Thirty-two focused archive/audit tests pass, including cross-filesystem copying,
all Bayer phases and Malvar borders, valid-sample thresholds, closed-form carrier
responses, FFT bands, source/capture weighting, report coverage and native cells.
A source-frozen proof audits **17 genuine retained observations** from earlier
photo, adverse-camera, carrier/flat and color runs. Maximum photo PSNR discrepancy
is .0000021dB; camera/color arithmetic agrees exactly and carrier/flat differences
are below 1.7e-14. Both generated native triplets were actually viewed. This is
engineering verification, not a new model-quality experiment.

The proof exposed and preserved two setup failures before any prediction record:
an output above the frozen workspace boundary and a cross-filesystem hard link.
Fresh corrected output roots and the tested copy fallback resolve them; original
sources, logs and partial files remain unchanged. The queued audit writes inside
its own frozen workspace and requires 8GiB available RAM and 2GiB output space.
Failures stop with evidence preserved and no automatic retry.

The trained endpoint results remain pending. Useful measured gains can advance
the docs and implementation without a historical promotion gate freezing the
model choice.

## Incremental V116 evaluation

The [V116 data trial](fine-detail-data-training.md) has completed training, with
a separate evaluator running and CPU audit queued behind that exact owner.
It declares one new checkpoint:
4,586 model/encoder calls and 14,190 numerical observations, with the same
material, analytic, camera and standing GFX/full-frame coverage. The original
V114/V115 evaluation runs once and retains the matched V114 control outputs.
No control inference is repeated for the data-recipe trial.

The collector validates distinct declared checkpoints and complete archive
coverage for one or two models; the independent queue checks the declared model
and observation counts. Eleven new cases cover single/two-model archives,
missing/duplicated endpoints and internal/legacy-external queue plans; the
28-test identity/archive/queue suite passes. Original waiting queues keep their
frozen sources and owners.

V116 outputs stay inside its frozen internal workspace. Phase starts require
128 GiB internal free, with 96 GiB reserved at runtime and 208 GiB external free
for the read-only input store. These new limits do not change the original
queues' guards. The [matched V114/V116 source/scene join](fine-detail-data-training.md#matched-saved-output-comparison)
is now queued after both exact independent audits. It checks input, target/mask
and display identity, reuses the independently rebuilt metrics and prepares a
Markdown report with native material triplets and all six full-frame GFX regions.
No control inference is repeated. Actual native viewing remains pending before
a data-recipe quality conclusion.
[Source and queue receipt](results/v116-detail-data-queued-v2.json).
