# Mixed-domain optimizer updates and measured execution choice

Implemented grouped source batches with unchanged global data indices, per-group
supervision and per-data-step noise RNG. Effective16 supports four B4, two B8 or
one B16 forward, followed by one clip/Adam/EMA update. Default grouping1 keeps
the old update operators. New checkpoints/logs retain optimizer/source/example
counters, and resume rejects changed layouts, source batch size or EMA decay.

105 CPU checks pass plus the separately executed CUDA RNG check. Real mixed
Commons/native/paired stop/resume matches weights/EMA/Adam/RNG and every source
fingerprint for all three layouts. Accumulated gradients match a joined batch,
including a case requiring clipping. The legacy default matches archived CPU
training-loop weights, EMA, moments and RNG.

The actual GB10 FP32/channels-last sweep selects B4 accumulation. No-DINO
throughput is14.577/13.469/12.067 examples/s for B4/B8/B16; DINO gives
13.764/12.951/11.527. Allocated peaks are4.74–4.88GiB for B4 versus18.23–18.43
for B16. Four excluded warmup and16 timed updates per point, cached data only;
no full-pipeline speed or quality claim. All model/gradient/Adam states, genuine
frozen DINO and fixture hashes verify; benchmark weights discarded. Independent
replay checks six timing points and all21 inputs/47 guards after exact owner exit.

Prepared fresh V72/V73 effective16/FP32/gain32/residual÷32 recipes on unchanged
manifests. Preserve640k-example horizon, warmup8k examples and first32k gate.
The controller first checks a genuine12-update prefix and portable checkpoint,
then restores model/Adam/RNG state before continuing to2000 optimizer updates.
Actual data preparation and common initial states are recorded. Full quality,
native crops and GFX foliage/fence review remain necessary; no promotion follows
from the fixed-training-set diagnostic or execution sweep.
