# Test a reconstruction objective from the stronger mature DINO parent

Previous goal turn was progress: committed/pushed actual opt-in FP32 inference,
full mature-model output/export checks and native views. Quality/SOTA and sub10s
remain unmet. The completed mixed16 RAW pair is much worse than the mature RGB
network, so no automatic extension of that weaker pair follows.

Added training-only `reconstruction_objective: image-log-mse-v1`. It replaces
primary synthetic camera/rendered and paired measured-CFA/coarse-rendered losses
with per-image negative PSNR, floor1e−10/100dB ceiling, FP32 reductions and existing
validity masks. Other auxiliary/gradient/highlight terms keep definitions and
coefficients; relative gradient influence changes. The default remains exactly
`charbonnier-v1`, ordinary/grouped data paths propagate the option, and resume
rejects a policy change. No inference/model parameter/source-image change.

Primary-source research revisited [JD3Net](https://arxiv.org/html/2601.00703v2):
PSNR loss is used for its synthetic experiments; the real HDD study instead uses
MSE. This is motivation for our controlled test, not a reproduced result or an
imported schedule/code/weight. Existing mature color/detail failures give a local
reason to test the objective mismatch with mean per-image PSNR.

Focused CPU suite:98 passed, one CUDA test skipped in32.00s. Added grouped log-MSE
integration coverage afterward:2 passed in4.90s. Ruff passes all changed code,
tests and three operators. Scalar/NumPy formula/gradient and masking/empty-target
checks pass. Old losses stay byte-identical. Actual CPU training resumes exactly.

Genuine V63-original20k CPU preflight completes control/log-MSE/2+2 resumed arms,
four discarded B1/native64 FP32 updates each. Identical observations, unchanged
frozen genuine DINO and finite91 model/91 EMA/89 AdamW states. Independent saved
model/EMA/optimizer/Python/Torch/CUDA RNG/best/step replay is exact. Production-size
CUDA preflight completes two fresh instances serially in one process, six updates
each at B16/native256/BF16/workers4+2+2. All six observations match;89 gradients
finite per update; DINO unchanged; independent replay finds89 changed model and
89 changed EMA tensors in each checkpoint. Peak allocations7.20/7.02GB. Log-MSE
preclip norms85–1008 versus control.057–2.545, so global clip1 is active on every
log-MSE preflight update. Engineering success is not quality evidence.

Prepared V74 control/V75 log-MSE from the same genuine V63 EMA, fresh AdamW/EMA,
original4k horizon/first1k boundary, LR1e−5/warmup100/seed51/B16/BF16. Both now
admit the previously fully cache-audited, reviewed and series-quarantined84,867
Commons4× training rows. Validation2303/test2255 assignments stay fixed;181 known
related-series/site rows remain removed. Native128/106 groups and paired32 data,
augmentation/physical noise/palette/fractions remain fixed. Against the ancestor,
data and optimization also change; only the loss family differs within this pair.
Ancestor training included related-series rows, which new exclusions cannot undo.
Review retains fixed418/416-source sensitivities and no scene-independence claim.

First frozen launch failed before any forward/update: its unchanged writable-path
guard rejected the outer repository's hot-cache run paths. Preserve its source,
plan/log/terminal status under `.cache/experiments/reconstruction-objective-v74-v75-first1k-v1/`.
Corrected v2 relocates only frozen run outputs inside its checkout, passes both
actual path checks and starts real training. No safety-code workaround, precision,
data, model, loss or gate change. New controller PID3651598/creation1792336209.54,
first child3651600/1792336210.2 were verified live after actual optimizer updates.
Their current status must be rechecked rather than inferred from this diary.

Active root:`.cache/experiments/reconstruction-objective-v74-v75-first1k-v2/`.
Frozen plan SHA256:`27da40cd2bc49be9037af4abeaa168efc02d7e07e856a5e3b3c42d297afaa883`.
Controller tool session89824. Each worker has a24GiB allocator cap/one-hour limit;
the two arms run serially and stop at1000, without automatic continuation/retry.
Outputs use authorized root hot-cache space to retain external500GiB reserve.
First16 and all41 logged domain/observation/LR records must match. Original photo
sources stay read-only; standing GFX/siblings and protected-final scenes stay out.

[Experiment and frozen review criteria](../docs/reconstruction-objective-v74-v75.md),
[preflight/public launch evidence](../docs/results/reconstruction-objective-preparation-v1.json).
Full427, known/unseen, analytic/hue/highlight and actual native synthetic-GT/GFX
views remain required after both owners exit. Passing local continuation criteria
would not establish model promotion, SOTA or the full requested end state.
