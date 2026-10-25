# Fine-detail data trial: V116 versus matched Tiny V114

**V116 is training after the completed Tiny/Small quality review.**
Its eight discarded CUDA updates passed before the original20k production run
started. [CUDA and launch evidence](results/v116-detail-data-running-v1.json). It tests fine
weak-texture sources and reviewed paired-reference masks with the same V112
Tiny architecture, parent, seed, schedule and 20,000-update budget as completed
V114. V114's completed evaluation supplies retained control outputs; its training
and evaluation are not repeated for V116. V116 has no trained-quality result yet.
V114 is the current general baseline after [complete Tiny/Small review](v114-v115-quality.md).
V116 retains its original explicit V112 parent and matched control.

[Recipe](../configs/quality-v112-fine-reviewed-v116.yaml) ·
[Completed preflights and live queue receipts](results/v116-detail-data-queued-v2.json) ·
[Original Tiny/Small comparison](small-aligned-training.md).

## Data changes with the architecture held fixed

| Setting | Completed V114 control | Running V116 |
| --- | --- | --- |
| Initial restoration weights | V112 final20k EMA | Same exact 91 tensors |
| Frozen encoder | Official DINOv3 ConvNeXt-Tiny | Same weights/revision |
| Commons / native corpus | 90,864 sources / existing native cohort | Same |
| Weak-source quota in Commons | .15 legacy | .075 legacy + .075 fine |
| Paired references | Original train32 masks | Four reviewed crop masks revised |
| Reconstruction epsilon | .0003 | .0003 |
| Normalized-band loss weight | Off | Off |
| Training | Seed63, fresh AdamW/EMA, native256/B16/BF16, 20k | Same |

The [fine profile](fine-weak-texture-coverage.md) supplies random-field frequencies
from 1/6 to .34–.40 cycles per final pixel and fiber periods of 3.5–6 pixels.
It replaces half of the existing weak allocation; photographic, flat, strong
procedural, native and paired quotas stay fixed. Geometry precedes the final
2× reduction, and optical PSFs remain disabled.

The [reference revision](paired-reference-quality.md) excludes neighborhoods of
one recurring red speck in two Nikon Z6 references. No intensity or noisy-input
array changes. It adds no photograph or scene. This is a combined data-recipe
comparison, not an isolated frequency-only effect.

The optional [normalized-band term](contrast-normalized-band-supervision.md)
remains disabled: its real parameter response was mixed, including adverse
alignment in both inspected faint high-noise cases. No new loss or architecture
change is bundled into this trial.

The deterministic schedule prospectively contains 5,039 paired / 4,993 native /
9,968 Commons batches. Of 320,000 planned samples, **11,767 use the fine profile**
and **26 touch a reviewed mask exclusion**, removing 4,508 measured samples across
those repeated draws. These are scheduled counts, not completed training or
unique-source counts. Noisy siblings in a modified batch can also change because
Poisson sampling consumes a variable number of RNG values; per-step seeding
preserves subsequent unchanged batches.

## Actual checks completed before queuing

The earlier legacy/fine trial already completed eight discarded CPU64/B16/FP32
updates per arm. Its 16 updates and complete source/state evidence are adopted
without rerunning them.

One **new native256/B1/FP32 V112 update** checks the revised reference path. A
declared engineering override selects paired index 1211, covering all 289
excluded samples in one crop. All 91 initial EMA tensors match V112; all 89
fresh Adam states reach step 1 and remain finite with model/EMA. The official
Tiny encoder stays frozen. Every nonmask input field matches the original
reader, and actual network-output gradients are zero at the excluded samples.
This discarded check is not the production prefix or a quality result.

Three actual native256/B16 reader/degradation prefixes compare the original
V114 source, the current source with legacy data, and V116. All eight default
clean and physical batches match **bit for bit across source versions**. The
candidate changes only clean indices 37, 39, 45, 117 and 120; six whole noisy
batches remain exact, and camera/CFA/WB/matrix/shot/read fields remain exact in
all eight. These checks generate 192 CPU degradation observations across three
variants, including identical control replays. CPU noise is not asserted
identical to CUDA noise.

Eight retained real CPU64/B16 predictions also reproduce every default loss,
term and **2,097,152 output-gradient elements** exactly across old/current source.
The physical model/noise/camera code, optimizer factory and EMA update stay
unchanged. The gradient replay adds no neural forward or new observation.

The new GPU worker and controller pass a real `__mp_main__` import probe with
training and module calls prohibited. This checks the multiprocessing guard;
the subsequent actual eight-update BF16/CUDA check also passed.

## Execution and complete quality review

The controller observed successful exit of the exact original Tiny/Small
independent audit. Eight discarded native256/B16/BF16 CUDA updates passed;
production then started fresh from V112 for its original20,000 updates. Expected monitoring adds 640 validation forwards.
Failures preserve work and stop without automatic retries.

CUDA preparation must match the completed native CPU clean prefix. Unchanged
input hashes, domains and learning rates are checked against V114's original
receipts; changed hashes must agree with the declared data schedule. The first
prediction/loss must match the original common V114 starting function and then
the candidate's own discarded check. Logged controls cover 801 production rows;
unlogged production tensors are not independently verified in full.

A separate evaluator is live and waiting behind that exact V116 controller.
It makes **4,586 new model/encoder calls**, retaining FP32 predictions and
supervision for all **14,190 numerical observations**, plus six standing GFX
contexts and a complete 102MP export. The independent CPU audit is queued too;
it prepares at least two native noisy/restored/exact-GT material triplets.
Real GFX references remain approximate and include foliage/fence.

The evaluator handles a declared single candidate, so existing V114/V115,
V112 and stronger RawNIND controls need no repeat inference. A dedicated
[matched comparison is now queued](results/v114-v116-matched-comparison-queued-v1.json)
after both exact independent-audit owners. It pairs all 14,190 retained V114/V116
observations; the candidate audit also reports against existing V112/RawNIND controls.
Actual material/GFX viewing and comparison of strengths and weaknesses remain
required. No statistical promotion rule or automatic recommendation change is
introduced.

## Matched saved-output comparison

The [comparison](../scripts/compare_quality_archives.py) selects exact checkpoint
hashes and inference policies across the two-model control and single-candidate
archives. It checks complete observation metadata and scoring protocols, then
requires identical noisy-input and logical target/mask/WB/matrix fingerprints.
It pairs independently rebuilt NumPy64 metrics without rereading every prediction
file or running the models again. Photo summaries weight sources equally; camera
summaries average crops within capture, captures within scene, and scenes equally.
Intervals describe these fixed sources/scenes, not training-seed uncertainty.
Color tails, carrier phase/residual and flat-field false texture accompany PSNR;
carrier gain is interpreted relative to one.

The [CPU controller](../scripts/queue_detail_data_comparison.py) also checks both
actual training receipts and the frozen recipes. All explicit settings agree
apart from the two declared data changes, run/notes and equal-content validation
protocol paths. Default-off fine-source and normalized-band settings are handled
explicitly. Same parent, model, seed, schedule and budget are verified rather than
inferred from version labels. The old generic Small status text does not override
the V114 worker's actual Tiny arm/backbone evidence.

[Native reporting](../scripts/compare_quality_crops.py) preserves both complete
candidate noisy/restored/exact-GT triplets and builds a noisy/V114/V116/GT board
without resizing any crop. Six GFX regions use the retained **unquantized FP32
crops of full blended 102MP outputs**. Noisy, restored and independent ISO100
reference floats share one NumPy64 exposure/WB/matrix transform. Reference source,
ROI and input pixels must agree across endpoints. ISO100 remains approximate and
receives no pixelwise score. All PNG cells are reopened and checked.

Twenty-five new comparison cases plus the sixteen existing arithmetic cases
pass. They cover a closed-form 6.0206 dB gain, mismatched inputs/targets/masks,
coverage, policy, protocols and display, recipe changes, completed owner/arm/budget
evidence, and six-region GFX rendering. A separate frozen readiness proof reuses
17 genuine retained method observations: two photo self-comparisons, two Tiny–Small
camera pairs, eight texture self-comparisons and three color self-comparisons.
The two native material columns were actually viewed. This is **engineering
readiness, not V114/V116 quality evidence**. It adds zero neural/encoder calls,
optimizer updates, noise observations or RAW decodes.

The waiting comparison requires 8 GiB available RAM and 2 GiB output headroom.
It writes a reviewable Markdown report, bound numeric results and native images
inside its frozen workspace. Existing six owners and sources remain unchanged.
Failures preserve evidence and stop without automatic retry. Actual viewing and
publication of useful measured gains/weaknesses follow when results are ready;
there is no statistical gate freezing the model choice.

New training/evaluation artifacts stay in internal SSD caches. Phase starts
require 128 GiB internal free / 48 GiB available RAM, with a 96 GiB internal
runtime reserve and 24 GiB CUDA model quota. External cached inputs remain
read-only with a 208 GiB reserve. The original running jobs retain their own
unchanged guards and budgets.

Eleven new cases test one/two-model archives, missing or duplicated endpoints,
complete audit counts, and incremental internal / legacy external queue plans.
Together with existing identity/archive tests, all 28 pass. Existing queues keep
their frozen two-model implementations; no old owner is replaced.
