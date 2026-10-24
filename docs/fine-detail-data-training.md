# Fine-detail data trial: V116 versus matched Tiny V114

**V116 is queued after the original Tiny/Small quality review.** It tests fine
weak-texture sources and reviewed paired-reference masks with the same V112
Tiny architecture, parent, seed, schedule and 20,000-update budget as completed
V114. V114's queued evaluation supplies retained control outputs; its training
and evaluation are not repeated for V116. V116 has no trained-quality result yet.
V112 remains the current learned baseline while the other endpoints are measured
and inspected.

[Recipe](../configs/quality-v112-fine-reviewed-v116.yaml) ·
[Completed preflights and live queue receipts](results/v116-detail-data-queued-v2.json) ·
[Original Tiny/Small comparison](small-aligned-training.md).

## Data changes with the architecture held fixed

| Setting | Completed V114 control | Queued V116 |
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
actual BF16/CUDA readiness remains pending.

## Execution and complete quality review

The controller waits for the exact existing Tiny/Small independent-audit owner
and successful receipt. It then runs eight discarded native256/B16/BF16 CUDA
updates. Only after they pass does production start fresh from V112 for its
original 20,000 updates. Expected monitoring adds 640 validation forwards.
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
V112 and stronger RawNIND controls need no repeat inference. Retained V114 and
V116 source/scene observations must be paired for the data-recipe comparison;
the candidate audit also reports against existing V112/RawNIND controls.
Actual material/GFX viewing and comparison of strengths and weaknesses remain
required. No statistical promotion rule or automatic recommendation change is
introduced.

New training/evaluation artifacts stay in internal SSD caches. Phase starts
require 128 GiB internal free / 48 GiB available RAM, with a 96 GiB internal
runtime reserve and 24 GiB CUDA model quota. External cached inputs remain
read-only with a 208 GiB reserve. The original running jobs retain their own
unchanged guards and budgets.

Eleven new cases test one/two-model archives, missing or duplicated endpoints,
complete audit counts, and incremental internal / legacy external queue plans.
Together with existing identity/archive tests, all 28 pass. Existing queues keep
their frozen two-model implementations; no old owner is replaced.
