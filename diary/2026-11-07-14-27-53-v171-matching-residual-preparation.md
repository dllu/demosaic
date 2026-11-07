# V171 learned matching residual on the frozen DINO result

Recorded: 2026-11-07T14:27:53-08:00 (America/Los_Angeles).


The V170 comparison established that its released weights weaken mesh response
and add periodic low-noise artifacts in this pipeline, despite better coarse
flat error. The next change uses the matching architecture as a fresh RGB
residual on the frozen V169 EMA result and cached V143/DINO parent. Width16,
nine neighbors per scale and39 inherited physical features give2,088,906 new
parameters/141 tensors, above124,909 frozen parameters/47 tensors. The RGB tail
starts at zero; released V170 weights are not used. All93 prior neural files
remain unchanged.

The run adopts all1,000 existing V168 batches and pair units, with no new media,
noise draws or parent/DINO calls. It combines pixel/gradient, paired-difference,
paired-common, flat-target and local/DC regret losses. The old spectral loss is
omitted; this does not isolate architecture from objective changes. ADC-only
rows skip updates, and zero supplied variance bypasses the new branch exactly.
The goal remains stronger fine strands with fewer flat-region artifacts; no
quality or noisy-flat safety gain is claimed in preparation.

All114 relevant CPU tests pass, including six new native phase/routing cases.
Eight independent sampler adjoint fixtures pass on CPU/CUDA,FP32/FP64,kernels1/3.
Full-network CPU/CUDA parity and native512 batch4 backward/native768 inference
pass, with6.26GiB admission peak. The pinned CUDA grad-input uses atomic addition;
its explicit nondeterminism warning is retained, rather than claiming exact
training reproduction.

Admission first stopped on an incorrect all-nonzero gradient assertion: the
upstream offset predictors have zero final layers, so50 earlier offset tensors
legitimately receive zero gradients initially. The second observation attempt
completed GPU backward but tried reading `.grad` from a non-leaf device copy.
The corrected check detaches the device input. Both failures, sources and logs
are preserved. Aggregate admission uses3 CPU matching-network calls,6 CUDA
matching-network calls,4 nested frozen-component calls and8 sampler-only calls,
plus3 discarded synthetic updates. There are no held-out calls in admission.

Training owner15136/create1794091054.6 was verified live after launch. A genuine
step8 checkpoint restores model/Adam/EMA/RNG exactly and continues at9 without
prefix replay. The fixed1,000-row run evaluates final raw and EMA endpoints on
all822 cached quality inputs afterwards. Full arrays are limited to36 native
cases:72 RGB+72 corrections;all1,644 rows stream metric/fingerprint/addition
checks. Both protected GFX scenes, priors, windows and JPEGs remain qualitative,
excluded from training, and original/dataz media are unused.

The new bounded trial declares52/114GiB local/external reserves plus.5GiB margin,
32GiB runtime RAM and24GiB CUDA; older study guards and receipts are unchanged.
The sampler library/source and exact frozen V169 component are hash-bound.

[Protocol and pending quality report](../docs/learned-matching-residual.md) ·
[Prepared sources](../docs/results/v171-matching-residual-preparation-v1.json).
