# Inspect the fixed native crops during the ADC quality evaluation

Recorded: 2026-10-21T22:43:05-07:00 (America/Los_Angeles).

Primary photo controller/worker and the secondary native dependency waiter
remain live under their original identities. Actual primary score-file growth
continues; no completed primary panel or secondary GPU worker yet.

Froze the first1,008 main-suite rows: the same first4 declared sources,9 methods,
7 conditions and4 CFAs. All784 shared V43/V95/classical/RawNIND cases and6,272
metric fields, including nulls, match the earlier completed palette evaluation
exactly. Eight shared preview triplets are pixel-exact. These are prefix checks,
not a complete primary score or uncertainty estimate.

Copied all12 preselected native photo triplets and sidecars byte-for-byte,
then used the frozen existing crop-board helper. It verifies common source,
ROI, conditioning/display/reference metadata, identical noisy/GT pixels and
unchanged160×160 cells. Actually viewed the resulting16 native cells, covering
all12 source/method triplets. No neural inference, noise or score recomputation.

Fabric: V98/V99 remain yellow/olive relative to the orange synthetic target;
V43 is closer in broad color. Fine cords remain attenuated across learned
methods. The building retains clean learned-model roof/window geometry and
smoother sky; V95/V98/V99 look close, without a convincing V99-specific detail
advantage. RawNIND retains fabric broad color better than the later endpoints
in these views but substantially softens building edges/window detail. No broad
winner follows from two selected cases.

Fixed fabric ISO12800/RGGB sRGB PSNR is40.570255/32.388939/30.437321/29.849318
for V43/V95/V98/V99; chroma MAE is.003802/.012539/.016694/.017957.
Building PSNR is35.393585/35.842186/35.847698/35.852226. These score the native240
interior of the256 tile; displayed native160 ROI is[48,48,160,160]. No pooled
partial mean or interval. Positive priors bypass projection in both new models.

The first CPU snapshot reader incorrectly treated protocol.json's receipt as
its nested payload and stopped before image processing. Preserved its source,
failure and first-batch bytes. A fresh CPU namespace uses the frozen YAML and
retains the exact same first1,008 rows byte-for-byte; no model or noise rerun. V2 scope
and reference-score-log/protocol hashes are recorded in its audit.

Published four new native triplets with exact sidecars, two per endpoint,
matching source/ROI/display and the explicit synthetic-GT label. The
[provisional review](../docs/v95-adc-training-quality-review.md) distinguishes
these examples from pending full metrics, camera/color/texture/GFX and
lower-noise native review. The
[observation receipt](../docs/results/v95-adc-fixed-native-photo-observation-v1.json)
has SHA256 `10c7c03ef9b6a3109fe5e9afeceb9624aea922c19716ca6b82672964aeab4e15`.
No checkpoint selection, new inference correction, training change, speed
work or promotion. V43 stays the reference; the full goal remains unmet.

