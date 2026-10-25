# Reviewed paired-data admission

New paired scenes require an exact, hash-pinned review before the training
loader can accept them. The registry now pins the [completed51-scene review](paired-extension-quarantine.md).
Its [separate opt-in extension](results/paired-train83-reviewed.json) contains83
publisher scene IDs/71 sampling groups. Existing recipes keep their original
32-scene manifest and sampling behavior.

The [training-reference quality review](paired-reference-quality.md) separately
checks all 576 base crops and prepares a mask-only revision for two reviewed
low-ISO references. It adds no scene or source and keeps the original manifest
and running comparison unchanged. Actual native256 reader/loss checks pass;
the revised targets were used in the [completed V116 trial](v116-quality.md)
and [V117/V118 comparison](v117-v118-quality.md). Those recipes combine mask
changes with other interventions or added training; the correction's isolated
quality effect remains unmeasured.

The embedded review payload records acquisition, protected/Commons screening,
prepared-target and manual-review SHA256s; protected scene names; and every
approved case including its noise conditioning, camera metadata, references
and absolute crop paths/hashes. Canonical JSON determines its review hash.
The loader accepts only an exact hash explicitly registered after review.
Self-signing a receipt or changing a quarantine split does not register it.

New cases must match their complete reviewed records. Unknown cameras,
EOSM100/GH1 aliases, existing train32 IDs, protected names and the conservatively
excluded scene families are rejected. Missing or duplicated reviewed cases,
changed conditioning/WB/path and corrupted NPZ files also fail. This contract
supports a later separate opt-in extension; it does not modify current recipes,
base/quarantine manifests, held-out data or private frozen training source.

Fifteen focused admission cases are covered by the CPU suite, which passes
**427 tests with eight CUDA checks skipped** in62.57s. Genuine GPU checks remain
queued behind capacity training in their separate frozen source. This count
does not claim those queued GPU checks ran on the newly added loader contract.

[Actual train32 compatibility receipt](results/paired-admission-legacy-parity.json):
the original immutable manifest,32 scenes, seed48 and native256 patches yield
identical tensors and SHA256s for ten declared indices under the previous
frozen loader and the new loader. Source versions and the driver are archived;
CUDA was not initialized. This is routing/sampling compatibility evidence,
not restoration quality or a new data admission.

Related reviewed views/exposures can share an explicit `scene_group`, including
an existing legacy group. The full case equality check binds that alias too;
changing it outside the receipt fails. Legacy cases keep their original groups.

The final CPU suite passes443 tests/eight CUDA skips in48.81s, including source
license checks, grouped sampling and the separate extension builder. The earlier
427 count above records the initial closed contract. Actual final-source train32
parity remains exact for ten samples; the new dataset also passes seven native256
sampling/determinism checks. [Frozen-source GPU validation](results/paired-expansion-v53-v54-launch.json)
subsequently passes451 tests in45.09s. Both actual datasets complete two
discarded BF16 updates at B16/native256 with genuine unchanged pinned DINO;
common initialization and portable FP16 reloads match exactly. The matched
quality trial [completes its first1000-update review](paired-expansion-v53-v54-review.md):
expanded photo PSNR+.09654dB with positive source interval, mixed real-camera
scores and subtle GFX native differences. Both arms then finish their original
[4000-step schedules](paired-expansion-v53-v54-4k-review.md). The early photo
gain disappears; real-camera differences remain uncertain. The expanded corpus
stays opt-in, with no model promotion or convergence claim.

Those V53/V54 results describe an older architecture and4000-update recipe.
They do not measure the extension on current ConvNeXt models or prevent a new
quality experiment. Current recipes still use the reviewed32-scene data.
