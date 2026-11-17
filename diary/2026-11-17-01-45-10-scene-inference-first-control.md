# Scene-context inference and first native control review

Recorded: 2026-11-17T01:45:10-08:00 (America/Los_Angeles).

Previous goal turn was progress: implemented/shared scene data/training, qualified
current mixed-domain execution and saved the first1000 larger-corpus updates;
commit8f18bf14 is pushed. Revalidated its exact owned controller/child live.

Added scene_inference.py: explicit raw/EMA loading, one noisy-scene encoding,
phase-preserving native ROI queries and bounded overlapping tiles. Reduce the
preview on CPU before moving that small field to the encoder device. Original
frozen training sources are unchanged.30 focused tests passed; actual CPU V120/
scene-wrapper checks on one reserved scene/two native256 crops reproduce direct
outputs exactly (4 wrapper/6 encoder calls across none/spatial). An initial CPU
qualification used nonexistent24/25 on this20-core host and stopped before model
or data; preserved original source/log, then explicitly admitted8/9, separate
from training12..19. No GPU inference interference.

Inventoried all427 primary-photo caches and exact original RGB crop locations.
All match;315 crops have odd source x and/or y. Added photo_scene.py to define
an even CFA frame without moving/resizing those crops, retain original scored
RAW/variance bit for bit and create a separately keyed noisy surrounding field.
Targets are never read as context. All4 CFAs/origin parities, original variance,
RNG independence and target interventions bring focused tests to47 passing.
This is source/geometry plumbing; actual primary CUDA/witness qualification and
known/unseen whole-capture context admission remain pending.

All3 declared2000-update horizons now complete unchanged. Training worker seconds:
none881.607330, pooled916.669446, spatial899.483109. Each has4000 scene visits,
3701 unique sources and16000 native crop examples. Their observation logs are
byte-identical, SHA256 f40e7982e473b4e6cd882eaabf21613ab751ba37875453d06efa559eb64c3484.
Endpoint hashes and raw/EMA/Adam/RNG/draw counters are bound in the report.

Prepared4 fixed noisy full-scene observations from the first2 reserved development
sources, shadow/ISO12800 conditions and4 native256 crops each. These sources are
held out from the2k continuations, not the parent's lifetime or the larger scaling
pool. Six existing main/cab contexts retain their exact inputs, both ROIs/profiles
and camera JPEGs. An input-only2-RAF audit confirms their full-scene sensor RAW,
WB/matrix and native512/768 coordinates exactly. Cached noisy RAFs only; no
independent reference or original spinning-drive media enters context.

CPU baseline predictions completed, but final JSON serialization refused NaN
metrics for empty highlight masks. Retained all10 predictions/log/source bytes;
recovered metric metadata as null without a neural replay. Missing final total
duration/post-model-hash receipt stays missing. New frozen collector source
finishes all3 endpoint collections. A renderer initially observed a still-live
collector before its terminal JSON; it produced nothing and its error log is
retained. Rendering followed verified terminal completion, with no inference redo.

Interim control-only native inspection preceded remaining-arm completion; no
horizon/data/threshold changed. Final matched quality review followed all3
completed horizons. Actually opened16 final native160 boards (8 development,
4 main,4 cab), alongside16 earlier control-only boards. Verified every PNG
panel equals its rendered native input pixels;48 per-arm triplets retained.
Two primary spatial GT triplets and both standing GFX maps are linked in the
[matched native report](../docs/whole-scene-context-native-review.md).

Small sky-heavy development means: V12047.99155/41.20822, local48.09642/41.27949,
pooled48.07297/41.27666, spatial48.09145/41.29035dB (shadow/ISO12800). Spatial
versus local−0.00497/+0.01086dB. Most paraglider rigging remains missing against
sky, as do fine cab crossings; foliage stays soft. No obvious new sky grid in
these fixed crops. These narrow means are not full427/camera scores or a reason
to change the general recommendation. V120 remains recommended.

Queued/started a frozen CPU64-source study to avoid choosing only two sky-heavy
scenes: all reserved64,2 conditions,RGGB,4 crops, all4 endpoints plus spatial
masked/shuffled context. Shuffle within equal valid-area strata preserves the
learned pooled descriptor even at padding; both a random fixture and actual
trained pooled-adapter check pass. Share one verified frozen whole-scene encoding
across the conditioned variants. Reuse16 correct predictions for the first two
sources; planned752 new roots/880 encoder calls,128 cases. Initial4 cases are
complete, exact owned PID1200370/create time in launch.json live. This is not an
independent scaling holdout/full427 panel; numerical closure and viewing remain
separate. No GPU/training/noise replay for reused cases or quality-based stopping.

The GPU controller has advanced to the matched20k scaling control. Long100k
remains at its immutable first1000 and will resume its original Adam/EMA/RNG/
source-order/LR horizon after the20k control. Full427/known-unseen scores for
the finished scene arms are explicitly pending; last comparable V120/V131
measurements and PSNR registry/chart remain unchanged. The no-scene endpoint
has an exact91-tensor legacy inference export, without duplicating neural work;
its original complete optimizer checkpoint stays authoritative.

[Sources, receipts and native evidence](../docs/results/whole-scene-context-native-review-v1/publication.json) ·
[Larger-corpus status](../docs/full-corpus-scaling.md).
