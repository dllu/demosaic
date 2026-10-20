# Implement and launch the matched late RGB/DINO experiment

The preceding goal turn made progress: the fixed GT-informed spectral split
completed and was pushed in fbb8436. It located high-noise periodic artifacts
in observation discrepancy and showed that even target-derived fixed Malvar
correction can damage displayed colors. No spectral policy was installed.
The complete PROMPT goal remains active; SOTA, decisive real-photo superiority
and100MP/10s are unmet/unproven.

I reread the current model/training interfaces and the primary PixIE July2026v3
paper. It motivates separating semantic pixel refinement from denoising, but
its RGB enhancement task does not establish Bayer restoration quality. The new
design is independent, with no upstream code/weights/data transfer. Existing
early DINO guidance stays in both arms, so this is not a semantics-free trunk.

The new optional head learns normalized stabilized RGB corrections after the
mature trunk and before the unchanged physical inverse. Inputs are64 decoder
features,3 predicted normalized RGB channels and21 existing physical conditions.
A32-channel projection and two depthwise3/5px neighborhood blocks lead to a
zero RGB output. Four zero-initialized projections of already computed frozen
DINO stages supply averaged scale/shift fields. V90 pools those fields globally;
V91 keeps their spatial coordinates. Both have100,547 new parameters/24 tensors,
the same20x head LR, one frozen encoder pass and no fixed CFA innovation or
target-informed forward. The default is none; legacy model states remain valid.

Unit checks verify common initialization/RNG/outputs/gradients, frozen detached
DINO, one encoder call, global versus spatial access, padded-coordinate cropping,
batch independence, mixed physical noise, CPU FP32/BF16 and portable nonzero
reload/missing-state rejection. The targeted suite passes61 tests,19 new.
The first full-suite command omitted PYTHONPATH and failed during collection;
the corrected complete CPU invocation passes1,512 tests with9 CUDA skips in
205.20s. All nine skipped CUDA cases then pass in2.61s. README's test command now
includes repository/script paths. No production expectation was weakened.

Both genuine V63 CPU/B1/native64/FP32 and CUDA/B16/native256/BF16 preflights
finish all16 mixed Commons/native/paired updates for global/spatial/restart,
retaining the original4000 LR horizon. Parent initial output replay is exact,
global/spatial initial state and gradient fingerprints match, all16 source/
forward/loss observations match, and final common RNG/source archives agree.
All115 model/EMA state tensors and113 AdamW states are finite with correct
counters. RGB and semantic projections learn nonzero weights. Genuine DINO
hash370a84…540fd stays frozen/eval. All47 current model modules are fixed.

I found the inherited 8+8 harness recreates the model in the same process.
To meet the protocol's process-boundary requirement, I added separate CPU/CUDA
workers resuming each preserved genuine step8 state. An initial supplementary
preparation assumed stdout start events were in metrics.jsonl and failed before
creating a replay plan or training. I also attempted the dependent CPU run before
checking that preparation exit; it immediately failed on the missing plan and
performed no training. Both failed preparation trees/worker sources are retained.

The corrected helper requires exact train steps1..8 followed by9; five parser
tests cover valid, missing, duplicate and wrong boundaries. New v2 workers
execute only updates9..16 in new processes. Their final model, EMA, AdamW,
Python/CPU/CUDA RNG, best, step and model config match uninterrupted spatial
exactly; all16 observation/log identities agree. These extra8 updates per
device are discarded engineering replays, not quality extensions. All original
and supplementary workers/controllers are verified exited before production.

The fixed protocol is docs/late-dino-rgb-v90-v91.md; the validation report is
docs/late-rgb-engineering.md, with complete binding receipt SHA256
ab3ebda5fa3d41c4f763d4651d63960e458b2176b25d30b653196aba0941a9b1.
An immutable production-plan.json adds both process-boundary certificates and
the regression receipts to the prepared base plan before any quality updates.
It binds806 inputs and preserves the same model/data/LR/gates/budgets. SHA256
a18f483213875463f02b50eff76fb112a4a7b662f1973742d0d4c6f3020e1d98.
Root: /mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1/.

Both original4000-update arms use reviewed88,508 Commons/native128/paired32,
native256/B16/seed55, original physical synthesis/targets/losses/augmentation
and genuine V63 original20k EMA. Both include the already verified common
physics cleanups. The historical V88 control is not substituted for a fresh
global-head arm. Full runs retain1000/4000 states and log all initial16 plus
every25th source/forward/loss identity; no automatic retry, extension or promotion.

Production controller888626/create1792481153.0 and control child889750/
1792481225.19 are verified live at07:29UTC. The actual training log reaches
step25 in the native domain. This is a live owned worker, not a status-only
wait. Spatial is queued sequentially. The48GiB-for60s launch gate,24GiB CUDA
quota,24GiB runtime RAM floor, root64GiB/external500GiB reserves and14,400s
arm/wait bounds remain enforced. No source-drive paths occur in the806 input
bindings, and no original photo or standing GFX source is decoded/modified.

Ruff lint/format and whitespace checks pass. Full trained quality/native review
is outstanding; no validation number was used to select or promote a model.
The eventual report must include exact-GT native triplets and all standing GFX
regions with accurate independent-reference labels. V43/README images remain
working evidence. The next action is to follow these exact live handles through
their original budgets, then perform the fixed full numerical/native review.
