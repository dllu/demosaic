# Both late RGB arms completed their original4000 budgets

V90/global and V91/spatial each completed4,000 native256/B16 CUDA updates from
the same V63 original20k EMA. Their exact controller and workers exited. The
frozen final-review reader independently accepts both original endpoints.
The [boundary receipt](results/late-rgb-original4k-boundaries-v1.json) is copied
byte-for-byte from the executed review, SHA256
`5e8b985412060273b6afe473af46959255d137d82f02aaefe39a861da9709599`.

| Endpoint | Retained checkpoint SHA256 |
| --- | --- |
| V90/global4000 | `ba40d88149726c48f90d33399cf6ee4666daad470bff82bdfddf994a5e5eb3c4` |
| V91/spatial4000 | `80ade7b792a8621c214d4450b9e0befa7d06be2d4797ecfaaa7227def9b609e7` |

Each retained4000 checkpoint matches its arm's final checkpoint. Both1000
checkpoints remain retained. All115 model tensors,115 EMA tensors and113
AdamW parameter states are finite, with correct counters and nonnegative
second moments. Optimizer groups remain89/24 parameters at1×/20× LR, with the
original4000 schedule and learned nonzero RGB/semantic head tensors.

Both arms share all176 prescribed source/forward/loss-input observations,
all161 logged source/domain/LR records and final Python/CPU/CUDA RNG states.
This audits the recorded observations, without independently replaying every
unlogged training input. Their common initial model and first-gradient hashes
agree. All47 actual archived training modules match the frozen review source;
source/data/validation identities and model configurations pass the reader.
Only the prescribed global versus spatial late-RGB mode differs between model
configurations. Neither arm resumed or extended its budget.

Executed reader:
`/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-review-v1/work/scripts/review_late_rgb_trial.py`,
SHA256 `37659dea57e84c8dcbba5a81658f37c5c54b6fac2e25365a34a3d9594dd8cf24`.
Review plan SHA256:
`12a4a0b4f2e585baf9266dc91a73321f1d2c8a567619f8c49f3676d5cef42a2c`.
The [frozen recipe](late-dino-rgb-v90-v91.md) and actual work trees are unchanged.

The [ten-stage quality queue](late-rgb-review-preparation.md) has completed its
boundary, known-noise and unseen-noise stages and started the full427-photo
stage. These are operational progress statements, not quality conclusions.
Independent saved-array checks, complete native boards and actual viewing
must precede interpretation of the new scores. Reports still require at least
two native noisy/restored/exact-GT triplets per model and the cached standing
GFX sky/building/foliage/fence and highlight comparisons, with the independent
ISO100 capture labeled as a qualitative reference. V43 remains the working
reference. SOTA, decisive native superiority and100MP/10s remain unmet/unproven.
