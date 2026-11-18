# Replicate local mesh support and measure scene preview scale

Recorded: 2026-11-18T13:21:01-08:00 (America/Los_Angeles).

Replayed the same optical fit and local RAW support on 24 disjoint
natural backgrounds. At ISO6400 the local fit lowers gap addition
from 29.19 to 12.96 DN16 compared with global transmission. Against
affine, the gain in gaps persists and the transmissive-wire RMS
difference spans zero. Lower-noise wire accuracy and the additive
role still favor affine. Viewed two native gains, an exact gap and
an absent rear wire. This is a synthetic replication above the same
Corpus 100k EMA, with the existing GFX review retained.

An audit of all matched ordinary training draws found the median
native query covers 10.02% of its scene. The standing GFX queries
cover 0.26% and 0.58%. The coarsest feature grid spans 64 native
pixels per interval in the median training draw and about 364 on GFX.
This quantifies a scale difference for a future context comparison.

[Fresh mesh comparison](../docs/mesh-background-transmission.md#replication-on-24-different-photographs) ·
[Preview geometry](../docs/scene-local-contrast-2400.md#preview-scale-in-training-and-gfx) ·
[Standing GFX checks](../docs/mesh-background-transmission.md#standing-gfx100s-checks).
