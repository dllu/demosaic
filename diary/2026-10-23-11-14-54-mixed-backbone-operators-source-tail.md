# Per-model frozen backbone identities and source tail review

Recorded: 2026-10-23T11:14:54-07:00 (America/Los_Angeles).

The quality operators now bind the parent and each arm to an explicit DINO
model, pinned revision and loaded-parameter SHA256. Training, queued reports and
RGB16 export verify the identity; existing plans keep their original shared
Tiny expectation. Only declared encoder differences are allowed in the model
configuration comparison. Restoration settings, ADC policy checks and the
numerical implementation remain unchanged. Source-freezing helpers include the
new validator, including operators that reuse earlier numerical snapshots.

Actual CPU checks used one V102-derived gate-zero Tiny initializer file for
both Tiny and Small, with fresh eight-update workers. Both loaded all 91 parent
EMA tensors exactly, retained their distinct frozen backbone hashes and produced
finite optimizer states. These are discarded integration fixtures, labeled
V105/V106 only inside their private plans, not quality endpoints. The reporting
queue produced 72 score rows with exact arithmetic; deliberately assigning the
Tiny hash to Small failed before any learned forward. A cached genuine GFX
512×512 foliage export produced six RGB16 TIFFs. All 4,718,592 channel values
reopen within .502 DN of the float inputs. This check decoded no RAF, initialized
no CUDA and did not export the whole 102MP image.

Fifteen native cells were viewed across the photographic and GFX boards. Weak
cloud/fabric detail and foliage remain soft; these checks establish integration,
not a quality gain. The ISO100 GFX view remains an independent qualitative
reference. The initial cached-export worker failed a syntax preflight before
inference; a corrected worker and fresh v2 plan completed, preserving v1 evidence.
The targeted identity/queue/ADC regression checks passed 119 tests; Ruff passed.
See the [completed operator receipt](../docs/results/mixed-backbone-operator-CPU-v1.json)
and [current execution documentation](../docs/training-execution.md).

The incoming loss scan's 576-source snapshot led to actual native inspection
of 13 additional identities: 26 native source/target panels, 13 context views
and two larger native 1024 views. Twelve sources remain eligible, including
real glass, architectural grids, transparent insect wings and natural material
detail. The tulip source has strong outlines and flattened/cellular texture in
the larger source view and an outlined binned target; record it for a future
quality withhold. This is a source-specific visible-quality decision, without
claiming a processing algorithm or rejecting a camera family. Cumulative actual
native inspection now covers 99 unique sources, with two additional future
withholds. The [review receipt](../docs/results/incoming-source-loss-prefix576-native-review-v1.json)
and [source comparisons](../docs/incoming-commons-quality.md) preserve exact
identities, ROIs, hashes, licenses and the incomplete ranking scope.

At 11:19 PDT the original V104 process had passed 6,500 of 20,000 updates,
and the CPU source scan had flushed 1,216 of 2,395 sources. Their exact owners
and the three waiting evaluation/detail/export controllers remain live. V104's
90,872-source manifest and all five active plans retain their bytes; neither
future withhold changes its running trajectory. V102 remains the recommended
completed model. A CUDA Small/Tiny quality experiment has not been launched.

The hot-pixel/linear-DNG feature was already merged and pushed in 77328d1;
its original validation receipt remains [here](../docs/results/linear-dng-feature-merge-v1.json).
