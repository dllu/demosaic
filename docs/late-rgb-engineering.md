# Late DINO/RGB refinement: engineering checks pass

The [fixed V90/V91 comparison](late-dino-rgb-v90-v91.md) is implemented and its
genuine-weight CPU/CUDA preflights pass. Two identical100,547-parameter learned
RGB heads differ only in spatial access to existing frozen DINO features:
global pooling versus spatial fields. The original4000-update quality runs are
launched sequentially. No trained-quality, throughput or promotion result
follows yet.

## Model and regression checks

The optional setting defaults to `none`. The new head consumes normalized
decoder RGB/features and the existing physical conditioning, then learns a
joint RGB residual before the unchanged inverse noise transform. It uses no
fixed CFA correction or target-informed diagnostic term. Existing earlier
DINO guidance remains in both arms. The four frozen feature stages come from
the existing encoder invocation; the head adds no encoder pass.

Zero RGB/modulation projections preserve the parent's initial values and
common gradients. Head construction preserves common RNG, and global/spatial
initial states match exactly. Spatial prompts upsample in padded native
coordinates and crop the tail. Tests cover detached/frozen DINO, one encoder
pass, global invariance/spatial sensitivity, batch independence, mixed noise
families, FP32/BF16 arithmetic, nonzero portable reload and missing-state
rejection, incompatible modes and exact optimizer groups.

The [targeted suite](results/late-rgb-targeted-tests-v1.json) passes61 tests,
including19 new head tests. The [complete CPU regressions](results/late-rgb-regressions-v1.json)
pass1,512 tests with9 CUDA skips; those nine cases subsequently pass on CUDA.
Five added restart-prefix tests also pass. The initial full-suite invocation
omitted repository/script import paths and stopped during collection; the
corrected command passes without changing expectations. The README command
now includes `PYTHONPATH=.:src:scripts`.

## Genuine mixed-domain training and restarts

Each discarded preflight uses genuine V63 original20k EMA and the official
frozen DINO ConvNeXt-Tiny. CPU is B1/native64/FP32; CUDA is
B16/native256/BF16/channels-last, matching intended training execution. Both
retain the original4000-step LR horizon. Control/global, spatial and a separate
8+8 restart arm each finish16 updates across Commons, native RAW and paired RAW.

Initial actual outputs replay the parent exactly. Both arms' initial model
hash is71104e…03e437 and initial gradient hash is equal within each device,
with signed zero canonicalized to match tensor equality. All16 recorded
source/forward/loss observations, domains, common LRs, source archives and final
Python/CPU/CUDA RNG match across arms. DINO remains frozen/eval with hash
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
The final model and EMA each have115 finite state tensors; AdamW has113 finite
parameter states, correct counters and nonnegative second moments. Both RGB
and semantic projections learn nonzero weights. All47 model source modules
are fixed across CPU/CUDA phases.

The inherited 8+8 harness reconstructs the model within one worker. To cover
the process boundary explicitly, an additional worker on each device resumes
the preserved genuine step8 state, executes only updates9–16, then compares
against the uninterrupted spatial endpoint. Model, EMA, AdamW, Python/CPU/CUDA
RNG, best, step and model config all match exactly; all16 observations and
scheduled log identities match. The extra eight updates are discarded
engineering replays, not quality-budget extensions.

The first supplementary preparation assumed process-start events were in the
metrics file; they are in stdout. It stopped before making a replay plan or
launching training. The failed CPU/CUDA preparation trees and helper sources
remain. The corrected parser requires the complete steps1–8 prefix followed
by step9, with missing/duplicate/wrong-boundary tests. New `v2` preparations
pass both actual fresh-process resumes. The original completed16-update
preflights and architecture are unchanged.

The [engineering receipt](results/late-rgb-engineering-v1.json) binds all plans,
statuses, checkpoint identities, finite-state counts, initial fingerprints,
source checks, supplementary failures and actual new-process comparisons.
Artifacts remain under `/mnt/external/demosaic/experiments/`:

- `late-rgb-v90-v91-CPU16-v1/` and `late-rgb-v90-v91-CUDA16-v1/`;
- `late-rgb-v90-v91-{CPU,CUDA}-fresh-resume-v1/` failed preparation provenance;
- `late-rgb-v90-v91-{CPU,CUDA}-fresh-resume-v2/` completed process-boundary audits.

## Original quality budgets now running

The new immutable `production-plan.json` adds both process-boundary
certificates and regression receipts to the prepared base plan before any
quality updates. It binds806 inputs; model/data/LR/budgets/gates stay exactly
as specified in the fixed protocol. Production-plan SHA256:
`a18f483213875463f02b50eff76fb112a4a7b662f1973742d0d4c6f3020e1d98`.
Root: `/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1/`.
The live `status.json` is operational state, not a completed quality receipt.

One arm runs at a time, with48GiB available for60s before launch,24GiB CUDA
quota, root64GiB/external500GiB reserves and14,400s arm/resource-wait bounds.
Only the exact owned worker may stop at a bound. Source-drive paths are absent
from all806 input bindings; training uses prepared local/SSD data. GFX3879/3880
and siblings remain excluded. No source capture is modified or decoded here.

Only original4000 endpoints can enter the required full FP32/native review.
Reports must include at least two native noisy/restored/GT triplets per model
and the standing GFX sky/building/foliage/fence plus sign/platform comparisons,
with independent real-photo references labeled accurately. Protected-final
scenes stay closed. V43 and its README crops remain the working evidence;
SOTA, decisive real-photo superiority and100MP/10s remain unmet/unproven.
