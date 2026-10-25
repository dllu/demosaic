# Latest cleaned corpus passes source-preserving native reader preflight

Recorded: 2026-10-25T05:54:16-07:00 (America/Los_Angeles).

The latest90791 cohort now has a completed source-preserving schedule and actual
augmented-reader preflight, beyond its earlier constructor-only membership
check. [Public receipt](../docs/results/cleaned90791-source-reader-preflight-v1.json).
The prepared membership, source pixels, model selection and running V117/V118
recipes remain unchanged.

Under the original seed64/native256/B16/20k data recipe, ordinary filtered-index
sampling changes98,605 of112,330 photographic source draws across all10,032
Commons batches. Referencing the original90864 ordered identities changes only
67 draws in66 batches, with unchanged source-selection RNG for every unaffected
draw. Domain allocation remains5013 paired/4955 native/10032 Commons batches.
The actual sampler's complete source-exposure counts match the metadata proposal.

The real new-cohort augmented reader checks107 native256 targets, including all
67 changed photo draws, retained and procedural controls, the six ROIs and four
nominal excluded-source draws overridden by an ROI. All40 unchanged targets
match their frozen-original FP32 byte hashes. All67 excluded draws produce new
eligible targets; no excluded or held-out cache reaches the future reader.
All21,037,056 future FP32 clean values are finite;7,864,320 unchanged values have
matching original hashes. This is not a pixel-level enumeration of all112330
augmented outputs.

All55 current reader source files are exact to the prior checked implementation.
Reuse93 original target hashes and the prior default-reader equivalence checks;
generate only14 additional frozen-original clean targets for newly affected
indices. There is no default-control replay, neural forward, physical-noise draw,
optimizer update or RAW decode. Torch is imported for the actual dataset only;
module calls are forbidden, CUDA remains uninitialized, and global Python/Torch
RNG states remain unchanged. Metadata schedule analysis imports no Torch.

This prepares the subset for later training without preselecting the next model.
For an isolated source-curation comparison, a corresponding completed V117/V118
control may be reused if initializer, loss coefficient, seed, optimizer/LR,
horizon and all other recipe settings match; actual new production-prefix checks
remain necessary. A later continuation can also choose a different useful
baseline and report its broader training scope. This receipt does not claim a
new neural trajectory, completed training or restoration gain.
