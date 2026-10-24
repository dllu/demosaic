# Queue V116 fine-detail and reviewed-data training

Recorded: 2026-10-24T12:30:29-07:00 (America/Los_Angeles).

Previous goal turn was progress: 7a3960f completed all 576 training-reference
screens, native review, the narrowly reviewed four-crop mask revision and its
real reader/loss checks. This turn moves that data and the previously checked
fine weak profile toward an actual matched quality trial. Initial live checks
at 11:52:33 PDT confirm original training 867877/1792848017.25 on V115 step 2675;
evaluation 986158/1792855221.87 and CPU audit 986159/1792855223.35 remain waiting
with zero children/stages. Previous V114 Tiny completed its original 20k.

Prepared V116 from exact V112 Tiny EMA, seed63, fresh AdamW/EMA, the same native
256/B16/BF16 geometry, LR1e-5/warmup200, reconstruction epsilon .0003 and original
20,000 updates. It combines fine weak quota .075 inside weak .15 with the
reviewed paired-reference manifest. Other Commons/native data and domain quotas,
photographic contrast/ROIs, zero optical PSFs, architecture and frozen official
Tiny remain fixed. Normalized-band supervision stays disabled because the
actual parameter response was mixed, including both faint high-noise examples.
This is a combined data-recipe comparison, not a pure frequency-only ablation.
Completed equal-budget Tiny V114 provides the control without another training
run. A useful trained Small result can independently advance the architectural
recommendation; this explicit-parent matched trial does not freeze that choice.

Adopt the already completed eight legacy plus eight fine CPU64/B16 updates,
preserving their exact workers/plans/checkpoints and failures. Do not repeat
those successful learned updates to prepare another recipe. One genuinely new
native256/B1/FP32 update checks the reviewed mask path from all 91 exact V112
EMA tensors. An explicit engineering getter override substitutes paired index
1211 for the requested first index 0, covering all 289 exclusion samples.
Every nonmask field matches the original reader. Actual prediction gradients
at excluded samples are zero with the full paired objective/auxiliary path.
All 89 fresh Adam states reach step1 and remain finite with model/EMA; official
Tiny stays frozen without gradients. This is one new root/encoder forward and
one discarded optimizer update, no validation/CUDA/noise/RAW decode. It is not
the production prefix or an improved-model quality measurement. The source
archive is 707abdcea6f3e14a48a7d6ebc7f1769e3da8e96d8959d856fcfc32961787075b.

To justify reusing V114, replayed three actual native256/B16 first-eight data
prefixes: its executed source, the current source with original data, and the
candidate. Dataset constructor expressions are extracted from each real trainer,
and actual domain samplers/preparation functions are used without a model.
All eight old/current default clean and degraded batches match byte for byte.
The candidate changes exactly clean indices 37,39,45,117,120 in steps3/8.
Six complete noisy batches remain exact; CFA/colors, WB/matrix and shot/read
fields match in all eight. Save every clean/batch field and cache-file binding.
Each variant reads the same 105 cache arrays. These are 384 sample draws and
192 generated CPU degradation observations, including identical control replays;
the paired samples reuse real captures. CPU noise is not asserted equal to
CUDA noise. Variable Poisson RNG consumption changes some unchanged siblings
inside modified batches; per-step seeding preserves subsequent unchanged ones.

Reused eight saved real legacy V112 CPU64/B16 outputs/batches to compare the
old/current objectives. All eight losses/terms and 2,097,152 output-gradient
elements are byte exact. Sixteen output-gradient evaluations occur, with zero
network Jacobians/forwards or optimizer updates in that check. Physical model,
noise/camera, precision, pretrained trunk, CFA and DINO code are byte unchanged;
optimizer-factory and EMA function ASTs also match. Added optional loss work is
skipped at weight zero. The expected source differences are the fine/default-off
loss plumbing and earlier evaluation-only archive callbacks. This does not
prove every unlogged production tensor or every possible image shape by replay.

An independent deterministic schedule enumerates 5,039 paired / 4,993 native /
9,968 Commons steps, 320,000 planned sample draws. It predicts 11,767 fine targets
and 26 draws touching reviewed exclusions, removing 4,508 measured samples across
those repeated patches. Integral-image checks prove every possible even native
256 patch in the four revised caches stays usable, so mask revision cannot
change the first valid-position choice. All 801 completed V114 logged domains
and learning rates match the schedule exactly. Counts remain prospective;
unlogged production input tensors are not independently observed in advance.

New source-frozen GPU wrapper/controller pass real `__mp_main__` import probes
with training/module calls forbidden and no CUDA initialization. The wrapper
requires all first8 actual GPU clean batches to match the native CPU reader;
changed/unchanged GPU hashes must follow the declared data schedule relative
to original V114 controls. First output/loss must match the original shared
V114 starting function and the candidate's own discarded CUDA check. Fresh
20k production follows successful eight discarded CUDA updates, preserving the
original LR curve and all source/failure receipts. Expected production monitoring
adds 640 validation forwards. No automatic retry or recommendation change.

The new training controller is live at 1241483/1792869685.22 and waits for exact
original audit 986159/1792855223.35 to finish successfully. It also requires the
old GPU owners to have exited before starting CUDA. It does not signal or
replace an original owner. The new output root is internal SSD storage, with
128 GiB free before phases / 96 GiB runtime reserve, 48 GiB available RAM and
24 GiB CUDA model quota. External inputs are read-only with a 208 GiB reserve.
The earlier jobs retain their original limits and budgets. Source/data/parent
guards run before execution; failures preserve attempts and stop.

Generalized the retained-output collector and queue preparation from hardcoded
two endpoints to a declared nonempty unique checkpoint set. Declare/validate
identities before neural work, require every model in collected results and
archives, and check independent observation counts against the declared model
count. New internal-storage queue paths have explicit reserves; legacy external
plans retain their defaults. These changes allow V116 alone to run, instead of
repeating the already planned V114 inference. All original copied queue sources
remain unchanged. Eleven new cases cover real one/two-model archives, invalid
or missing declarations, incomplete observations and internal/legacy external
queue preparation. Together with existing identity/archive cases, 28 tests pass
in1.29s; Ruff passes the three edited scripts and new test file.

The single-candidate evaluator is live at1241857/1792869857.91, waiting for the
exact V116 training controller. It declares4,586 new model/encoder calls,
14,190 numerical observations and the six standing GFX contexts/full102MP
export, retaining native FP32 outputs/targets. The independent CPU audit is live
at1241899/1792869888.87, waiting on that evaluator; it expects one model and all
14,190 numerical observations, with two native noisy/restored/exact-GT material
triplets. Full GFX references stay approximate and include foliage/fence.
V114's original evaluation/independent archive will supply the matched control;
pair its retained observations with V116 and inspect actual native/GFX behavior
before a data-recipe conclusion. The candidate audit also uses existing
V112/stronger-RawNIND controls. No control inference is repeated for V116.

Published the recipe, [current trial documentation](../docs/fine-detail-data-training.md)
and [corrected machine receipt](../docs/results/v116-detail-data-queued-v2.json),
and updated README/current-model, data, research, requirements and evaluation
docs. No new PSNR point or trained-model native gallery is invented. A publication
label in v1 accidentally duplicated the training-plan binding under `parent`;
its `explicit_checkpoint_parent` and all actual plans already named the correct
V112 checkpoint. v2 corrects only that label, binds v1/source and preserves all
receipt bytes. No learned or noise work is repeated for this metadata correction.

Actual new learned work this turn is one V112 root forward, one Tiny encoder
forward and one discarded CPU optimizer update. The native data compatibility
study generates 192 CPU observations including control replays. Retained-output
gradient checking adds 16 output-backward evaluations without a network call.
No new CUDA work, RAW decoding or external download occurs. Original picture
sources and caches, standing GFX siblings, held-out references and the16-scene
reserve remain unchanged. V112 stays selected while new quality is pending.

Training/preflight workers, source archives, plans, arrays, all actual output
gradients, mask update, deterministic schedule, compatibility evidence, control
provenance, spawn probe and launch receipts are under
`.cache/current-quality-20261023-v1/V116-detail-data-training-v1/`.
The separate evaluator/audit directories are siblings
`V116-detail-data-quality-v1/` and `V116-detail-data-independent-audit-v1/`.
All six old/new exact owners remain live at12:37:12 PDT; only the original
V115 worker has GPU children, latest logged step5725. Internal free792.14 GiB,
external254.08 GiB and available RAM80.08 GiB. The new three controllers have
zero children/completed stages. Preserve their ongoing budgets and dependencies.

This is progress toward the full PROMPT.md objective, not its completion.
Fine high-noise structure, broad real-camera superiority and100MP/10s remain
unmet or unproven. Quality stays first. Continue the original Small/quality
review, document useful gains directly, and let the queued matched data trial
test the concrete fine-detail and clean-reference interventions.

Final verification at12:42:33 PDT passes597 unique file bindings, all six
current frozen training/review plans and294 local Markdown links. Both the
corrected publication parent and recipe identify exact V112 SHA21c3cca8… .
No existing machine receipt, instruction or model-library file changed. All six
exact owners remain live; V115 is at logged step6075 and the five waiting
controllers have zero children or completed stages. Preserve the final verifier,
result and log locally. Staged whitespace is checked before commit/push.
