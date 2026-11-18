# Expanding whole-scene coverage to 90,692 photos

Recorded: 2026-11-17T16:51:37-08:00 (America/Los_Angeles).

I admitted 66,032 more prepared bin4 fields for whole-scene training by
using a 512-pixel minimum short side with the existing 4MP cap and native256
crops. The resulting 90,692-source set retains the pilot training sources
and reserves its development fields. The checked epoch order visits the
full set at update 45,346 with two scenes per update.

All four CFA patterns pass CPU preview, crop-slice and replay checks in
both size bands. The local-only and spatial models then each complete two
discarded optimizer updates from V120 on the same four scheduled scenes
and 16 native crops. The expanded scene run needs a held-out quality
comparison. The separate V120 100k continuation has saved its 48k
checkpoint, with two complete photo passes already audited and its 50k
native review queued.

[Expanded scene corpus and receipts](../docs/expanded-scene-corpus.md) ·
[Full-corpus training](../docs/full-corpus-scaling.md).
