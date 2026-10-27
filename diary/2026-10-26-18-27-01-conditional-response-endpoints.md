# Queue trained endpoint conditional bias and noise review

Recorded: 2026-10-26T18:27:01-07:00 (America/Los_Angeles).

The previous turn made progress by completing and publishing the loss-gradient
study. Revalidated the live original V123 worker993796/controller4066396 at
step3700, and all original and V124/V125 downstream owners, before proceeding.
The new evidence motivates checking actual trained conditional bias/variance,
not treating a3% output-gradient change as a model-quality gain.

Implemented a deferred repeated-noise endpoint queue. It waits for the exact
V124/V125 full quality and green-mesh owners to finish and exit, then resolves
only their original immutable20k checkpoints and recorded full model/backbone
identities. It uses the actually frozen quality source and the same128 stored
observations per new model: four targets/four CFAs/eight independent noise
draws, unchanged ISO12800/ADC conditioning. The256 original V120/V117 outputs
are retained controls, with no neural reruns. Planned new root/encoder calls:
256 each; reference NN/noise/RAW/optimizer work:0.

The collector checks loaded91-tensor EMA, original quality model hash, official
frozen DINO hash, all5 actual input fingerprints before each forward, IEEE FP32,
actual root/encoder counts and unchanged model state. Already evaluated model-
state hashes cannot silently trigger another neural run. No automatic retry.
The source audit found only the disabled RAW-frequency extension in the model
operator. A restricted AST specialization removes that disabled support and
proves both model/pretrainedRGB modules identical to the control operator; all
other inference modules match. Runtime requires the feature disabled.

The NumPy reporter analyzes CFAs separately, retains signed finite-draw bias,
reports all target-defined contrast strata and prepares8 single/mean8 boards
plus4 native exact-synthetic-GT triplets. Mean8 uses independent observations
and is not a single-capture inference mode. Native camera references remain
approximate, labeled notGT. Sources/ROIs/checkpoint/noise/exposure/WB/matrix are
retained with the image metadata. Primary useful gains need not wait for this
supplement; no new promotion gate or automatic model selection.

Twenty-four tests pass, covering exact-owner completion, partial/changed model
metadata, observation membership, squared-bias/variance, CFA averaging, fine-
band gain and disabled-feature source equivalence. The real CPU contract proof
resolved completed V121 SHA40fb6369... and never launched its collector. The
first standalone reporter proof lacked its parent output directory; preserved
its frozen source/log/claim, fixed parents=True, and prepared a new proof root.
Both attempts used0NN/noise/RAW/optimizer calls.

The successful retained-control replay reproduces all32 original group result
dictionaries and8 CFA-average dictionaries byte-exactly under canonical JSON.
All8 boards and2 native triplets match original reviewed output cells across
2,918,400 channel values. Actually viewed both exact-GT triplets, native grass
reference board and fur mean8 board; labels and native pixels are correct.
No old model forward was needed for the reporter/checkpoint handoff proof.

Launched the frozen supplemental queue at
.cache/current-quality-20261023-v1/V124-V125-conditional-response-v1, owner
1228088/create1793064204.15, waiting for exact new mesh1135940 and quality1135923
owners. It has a14-day dependency window,48GiB launch/32GiB runtime available
RAM,12GiB CUDA cap,128/96GiB internal start/runtime reserves and208GiB external
reserve. Collection/analysis budgets are2h/1h. No prior controller or worker was
signaled or edited. The model/corpus/ROI/noise/training plans remain frozen.

[Current panel and queued endpoint response](../docs/conditional-noise-response.md) ·
[Setup, owner, source and actual proof receipt](../docs/results/conditional-response-queue-setup-v1.json).

V120 remains recommended. Actual V124/V125 quality, SOTA, broad real-camera
superiority and100MP/10s remain unproven.
