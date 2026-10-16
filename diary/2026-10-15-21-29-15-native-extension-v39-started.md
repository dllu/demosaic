# Native extension V39 started

Started a separate native-data-only trial from the same V34-step1000 EMA as
V37, fresh AdamW/EMA, seed47, batch16, LR3e-5/planned3000, stop1000. Same full
RGB architecture, complete Commons4, paired data, mix and original8× validation.
Only native membership changes53captures/31scenes to59/37. Six outdoorCC0 RAWs
have reviewed source/cache/metadata admission; no new private or held-out scene
enters training. CanonM100 andDMC-GH1 held-out camera models do not overlap the
six additions; standingGFX still excludes its scene/siblings, not everyGFX camera.

Before training, compare against the actual V37 runtime source bundle. All
model, numerical augmentation, degradation, trainer and evaluator modules match
byte-for-byte. The only source changes are native admission validation and its
new helper. Replay one deterministic sample for each of all53 legacy captures
through both old/new loaders: all exact tensor hashes match. The proof and exact
workflow are archived in the run directory. Commons/paired logged observations
must match V37 after training; changed native draws are the intended treatment.

Controller PID627272, worktree .cache/native-expansion-worktree on branch
native-expansion-pilot; source imports remain isolated from subsequent work.
Status /mnt/external/demosaic/runs/native-expanded-v39-workflow.json. Log
.cache/native-expansion-worktree/.cache/native-v39-workflow.log. Parent is the
immutable evaluated4da823... snapshot. First1000 training only; development
review is required before continuing or promoting. No quality gain assumed.

Use cached V34/V37 comparator results only with explicit matching protocol,
input/target and executed-code checks; evaluation reuse should avoid repeating
unchanged GPU work. New-model real/full427/fullGFX and native crops remain required.
All304 tests passed before source freeze. The overall PROMPT goal remains active.
