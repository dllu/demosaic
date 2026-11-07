# V172 local noise matching preparation

Recorded: 2026-11-07T15:33:41-08:00 (America/Los_Angeles).


V171 made progress on standalone-flat error but worsened quiet color beside
structure. Its selected-array diagnosis found that attenuating the correction
by local supplied noise RMS helps more than removing a single global RGB mean,
but still loses to V169. This motivates retraining with local input and output
noise units, rather than treating the posthoc attenuation as a finished model.

V172 keeps the same2,088,906 trainable parameters/141 tensors, seeded initial
weights, frozen V169 EMA/V143-DINO parent, V1681,000-row cache, pair units, V171
criterion, AdamW/LR/clipping/EMA and schedule. Preparation verifies training,
runtime/resource/restoration ASTs, criterion bytes and all relevant recipe
fields. Only the new feature coordinate system and output amplitude change
jointly: local Bayer-cell RGB means/noise RMS replace image-wide statistics.
The criterion's image-wide units remain unchanged. No released V170 weights.
All95 prior neural source files remain unchanged.

All126 relevant CPU tests pass, including12 new independent cell-statistics,
locality, four-CFA phase, signed-zero routing, uniform-field and initialization
checks. New synthetic admission has4 CUDA wrapper/matching/frozen-component
calls,13 images,20 nested sampling forwards and3 discarded updates. Three
batch4 native512 backwards and native768 inference pass at6.26GiB peak.
Unchanged primitive/core adjoint and CPU/CUDA parity proofs are inherited from
V171 by source/library hash,not repeated or counted as new. The upstream atomic
CUDA input-gradient remains warn-only nondeterministic;no exact retraining claim.

The metric frontend is constructed under the actual frozen runtime before
training,without CUDA or neural calls,so the dependency omission from V171 is
caught before work. A routine current-preparer style fix adds explicit
`check=False` and parentheses;the originally frozen source is preserved,and
all training/review/runtime functions match it exactly. The readiness receipt
binds both versions. There are no failed V172 scientific phases at preparation.

Training owner83869/create1794094349.89 was verified live after launch. The
actual step8 model/Adam/EMA/RNG restoration continues at9 without prefix replay.
The planned raw/EMA review uses all822 existing cases,with exact frozen V169
replays and V171 EMA plus V169 EMA as baselines. Both protected GFX scenes,
priors/windows/JPEGs remain qualitative and out of training;no original/dataz
reads,new source/noise draws or parent/DINO calls. Zero local variance retains
V169 at that cell;this is not noisy-flat safety or whole-pipeline locality.

Only36 fixed native cases retain72 RGB+72 residual arrays;all1,644 rows receive
streamed metrics/fingerprints and addition checks. The60 native figures will
preserve160px pixels and all display/noise metadata without resizing. New
52/114GiB local/external reserves plus.5GiB margin,32GiB runtime RAM and24GiB CUDA
are declared before this run;prior guards and receipts remain unchanged.

[Protocol and pending quality](../docs/local-noise-matching.md) ·
[Preparation evidence](../docs/results/v172-local-noise-matching-preparation-v1.json).
