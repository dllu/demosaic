# V170 evaluates a recent learned RAW matching model

Recorded: 2026-11-07T13:48:26-08:00 (America/Los_Angeles).

The prior turn completed/pushed V169,which reduces quiet DC bias while retaining
mesh response but leaves spatial mottle and fine crossings. This turn researches
RAW-side matching. The April2026 [NLFeMF paper](https://arxiv.org/abs/2604.17453)
has a released learned matching/filtering network and weights. Its external RAW
training data differ from our free-image pipeline,so this is a pipeline comparison,
not an isolated architecture gain. [Protocol](../docs/nonlocal-raw-comparison.md).

Downloaded the pinned v1.0.0 source archive and rawnoise_25_15_9nbr checkpoint.
Published release digests match;original checkpoint SHA256
`b31bc8e21022389b0b209a9d1e6649485ed4dacc552b7ea04612df5f7515fcf2`.
Restricted weights-only loading initially rejects unused OmegaConf metadata;
inert metadata classes allow tensor extraction without arbitrary deserialization.
The141 tensors contain15,282,866 values. No old model/source bytes are changed.
MIT notices are retained,and kernel sources retain embedded Caffe notices.

The pinned CPU/CUDA sampler builds on the actual GB10 toolchain. Seven selected
network classes match upstream ASTs exactly. Four independent NumPy sampler
fixtures match both backends. The original/copy CPU models match bit-for-bit;
one CUDA parity forward differs by at most2.24e-8 normalized. These are two CPU
and one CUDA full-model calls,separate from quality.13 current CPU tests verify
independent native Bayer flips,exact inverse transforms,observed-noise-map use
and measured-sample consistency. The optional einops dependency is pinned0.8.1
in pyproject/uv.lock. Public fetch/build helper verifies and adopts existing bytes.

The fixed comparison uses822 unchanged cached cases and two returns from each
RAW-network call: direct Malvar,and DINO-parent plus Malvar of the measured-RAW
innovation. Full RGB stays unclipped;the RAW network input/output follow the
released0..1 clipping policy. The first processing cases cover512 and768 native
contexts,and their actual outputs are adopted into the same review.36 selected
native cases retain72 full RGB plus36 RAW arrays (.234GiB);other cases retain
streamed scores and fingerprints.48 boards/12 triplets preserve native160 pixels.
Both protected GFX scenes,priors and JPEGs remain cached/unscored/qualitative.
No new source/noise,training,parent/DINO or original/dataz reads.

Preparation failed before a plan because optional `output_shape` metadata was
missing on inherited cases;the corrected v2 root uses actual NPY headers.
The first v2 worker6276 then failed at a missing frozen profile helper before
claim/CUDA/input loading. Original files/logs remain preserved. A separate
preparation adds the unmodified helper,checks unchanged inference AST and all
original frozen files,and launches worker6399 under the same plan. No completed
scientific forward repeated. The worker is actually live and past209 cases at
this entry update;768 geometry has run,peakCUDA2.42GiB. Quality is pending.

The new bounded comparison uses52/114GiB local/external reserves plus .5GiB
projection margin and32GiB runtime RAM/12GiB CUDA. This is a new predeclared
footprint;prior experiments'56/116GiB guards/receipts remain unchanged.
[Prepared evidence](../docs/results/v170-nonlocal-raw-preparation-v1.json) ·
[Runtime correction](../docs/results/v170-runtime-dependency-preparation-v1.json).
