# A larger corpus for whole-scene training

The whole-scene reader can now use **90,692** prepared Commons photos, up
from **24,660** in the matched 2k pilot. The additional **66,032** caches
have a short side from 512 to 767 pixels at bin4. A native 256×256 crop
covers at most a quarter of any admitted field. The preview and crop come
from one noisy Bayer observation with the same camera, exposure, white
balance and sensor noise. This retains surrounding scene content while
keeping the original native measurements available to the restoration path.

The full-model 100k experiment is a separate run using 90,778 photos,
bin4 → geometry → area2 and its mixture of photographic, procedural, native
and paired examples. Its five complete ordinary-photo passes and 78,013
sixth visits have been verified from executed rows. The scene schedule uses native
bin4 targets, four crops per scene and global D4 transforms, as in the
original scene pilot. The matched context comparison can use a local-only
control on these exact observations. [Full-model training and review status](full-corpus-scaling.md).

## Source coverage

The corpus is a subset of the curated full-model training manifest. Every
selected row matches its original, including attribution and cache
checksum. It retains all prior scene training sources, reserves the same
64 scene development fields, excludes all 4,558 canonical validation/test
rows, and keeps the existing 4MP scene cap, which excludes 22 further
training fields. The candidate inherits the curated source exclusions,
including the protected GFX families. Preparation reads manifests and
samples existing binned caches.

| Updates at two scenes per update | Scene draws | Pilot pool, replacement | Expanded pool, replacement | Expanded pool, shuffled epochs |
| ---: | ---: | ---: | ---: | ---: |
| 2,000 | 4,000 | 3,701 | 3,916 | 4,000 |
| 20,000 | 40,000 | 19,778 | 32,397 | 40,000 |
| 50,000 | 100,000 | 24,239 | 60,509 | 90,692 |

These are counts of distinct **source IDs** in a deterministic schedule.
The first complete shuffled pass ends at update 45,346. The next 9,308
draws are distinct within the second pass. Crop, augmentation and
camera/noise seeds depend on the global draw index, so repeats still
yield fresh observations. Several crops of one scene share corruption
where they overlap.

## Reader checks

Eight actual cache reads span both short-axis bands and all four Bayer
patterns. All 32 native crops match their exact packed RAW and target
slices. The matching previews are finite and use the corresponding
scene coordinates. Repeating each draw reproduces its full fingerprints.
The expanded schedule uses the existing hash-bound photo order format
and checks its declared scene count and horizon at trainer startup.
[Reader audit](results/expanded-scene-epoch-corpus-v1/reader-audit.json) ·
[Independent membership and order check](results/expanded-scene-epoch-corpus-v1/independent.json) ·
[Preparation script](../scripts/prepare_scene_epoch_corpus.py).

The local-only and spatial arms each complete a two-update CUDA
qualification from the same V120 EMA. The arms consume the same first
four scheduled scenes and all 16 crop fingerprints match. Three of the
four scenes come from the newly admitted size band. Both initial outputs
match V120 exactly, the spatial adapter receives gradients, the frozen
DINO weights match their initial hash, and both checkpoints round-trip
model and Adam state. These updates were discarded after qualification.
[Matched model and data receipt](results/expanded-scene-epoch-corpus-v1/matched-preflight.json) ·
[Archived plan and log](results/expanded-scene-epoch-corpus-v1/publication.json).

## Quality question

The next matched comparison should ask whether spatial context preserves
actual thin structure in sky while suppressing false texture in smooth
regions within a busy scene. Keep the native measurement path identical
between arms. Compare correct, masked and shifted context as diagnostic
interventions. Score weak-detail and quiet-region errors separately and
review both standing GFX families at native pixels. At the smallest
admitted size, a crop covers a greater fraction of the field than in a
full GFX frame. The effect of that difference needs real-frame testing.
Restoration quality and long-run throughput remain open.
[Prior scene evidence and review protocol](whole-scene-context-next-test.md).

## Matched 12,000-update continuation

The expanded training has started from the verified full-corpus 100k
EMA `87b96f3c487b9edaf1c477742b6c38f2a82cc6b20a94716d51cc8cf46a17a760`.
The local-only and spatial arms each have a fixed horizon of 12,000
updates, 24,000 distinct scene visits and 96,000 native bin4 crops.
They use the same initial trunk, common shuffled epoch prefix and
canonical sensor-valid objective. Both optimizer schedules use a
100-update warmup with peak trunk rate `3e-6` and adapter rate `1e-4`.
The spatial arm adds the existing zero-output adapter at eighth
resolution. The architecture and loss otherwise match the prior
matched scene trial.

The first attempt stopped before any update because the scene loader
expected the original V120 digest. The corrected loader binds the
digest in the training plan and the saved scene checkpoint. Both
arms then passed two discarded optimizer updates on identical first
four scene observations from the new parent. The production
[local-only arm](expanded-scene-local12k.md) completed 12,000 updates,
24,000 distinct source visits and 96,000 native crops. Its scoped
development and both standing GFX views are complete. The spatial
arm finished its 12,000 updates with identical observations. Its fixed
weak-wire study and both standing GFX reviews are complete. The broad
comparison is collecting. [Spatial endpoint and native results](expanded-scene-spatial12k.md).
[Checkpoint bindings, preflight and start evidence](results/expanded-scene-12000-v2/publication.json).
The full training traces match all 24,000 scene records byte for byte,
including crop and noise fingerprints.
[Completed observation audit](results/expanded-scene-12000-v2/training-completion.json).

Both standing GFX families use the existing fixed native inputs with a
matched V120 and 100k comparison. The earlier 64 scene development
photos are excluded from this order, but the 100k parent has prior
exposure. The independent quality checks use the canonical held-out
panels and the constructed wire/gap intervention. The guide-specific
response remains small after expanding the scene training.
[2k wire and gap test](scene-wire-gap.md) ·
[100k parent](full-corpus-long100k.md).
