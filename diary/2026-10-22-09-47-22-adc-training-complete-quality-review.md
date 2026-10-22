# Close the ADC-training quality and native review

Recorded: 2026-10-22T09:47:22-07:00 (America/Los_Angeles).

All seven original evaluation panels and the secondary ADC/ISO100/ISO12800
native-photo diagnostic completed. Both controllers and all recorded worker
owners have exited. Frozen plans/inputs remain intact; no worker was restarted.
The full suite records17,824 joint forwards/DINO calls; the secondary adds12
forwards over48 joint observations. Every expected count, model/input witness
and explicit ADC sample-fidelity selection passes. These execution checks are
separate from quality.

Independent analytic coverage/arithmetic checks pass for2,240 rows and3,760
summary scalars, maximum difference2.22e-16. Rebuilt4,704 saved color predictions
and28,224 metric fields in Torch64, maximum difference4.44e-16; separately
verified864 descriptive summary fields. Secondary native coverage, arithmetic,
per-model counters and physical-input hashes pass; all108 scalar score rows
match their full-suite counterparts exactly across864 fields. No new inference
or noise for these CPU audits.

Actually inspected all10 original-resolution boards: photo, known, unseen,
analytic texture, colored flats, GFX, GFX highlights and three secondary noise
conditions. All96 primary and36 secondary triplets are represented by180 native
160px cells, shared noisy/reference cells counted once per case. The board
builder verifies every source PNG, shared metadata/noisy/reference pixels and
native crop dimensions without resizing.

ADC-only projection recovers orange fabric color and cords in both new models,
with V99's fixed fabric PSNR40.26683 versus projected V98's39.65199. This narrow
benefit does not persist at positive noise: ISO100 V99 remains yellow/olive and
scores21.12916 versus control21.31429. High-noise fabric also remains shifted
and smooth; building geometry is clean but supplies no convincing V99-specific
advantage. Real GFX sky/building/fence are coherent relative to RawNIND, foliage
texture remains smooth, and saturated sign boundaries remain imperfect.
DSCF3880 ISO100f/5.6 is separately captured with different aperture/time/LED
scan and is not exact GT. No pixelwise GFX ranking.

Full photo criteria already fail (+.02880362dB below+.03; ADC photographic SSIM
−.00203221). Additional failures: brighter .18-level/2%/16px high-noise carrier
gain V99.59553289 versus V95.61470861; high-noise worst centered color RMS
.00765520 versus V95.00405840/control.00738338; high-noise p95 channel bias
.00522483 versus V95.00520566. ADC color descriptors improve to p95bias.00018182
and maxcenteredRMS.00028490, below both95/control. Individual ADC carrier gain
loss stays within.05 (worst−.01106801), and all flat-case spatial RMS ratios
stay below1.25×95 (largest1.02343594). Preserve both passing and failing checks;
do not relax the criteria or extend final4k.

The [complete review](../docs/results/v95-adc-complete-quality-review-v1.json)
has SHA256 `eb78245067fd07d62b9f01dd3c3476af392681df9e88e8cc6cdfcfd49f9d5804`.
Published16 exact saved triplets/sidecars: both new models' six GFX regions and
ADC/ISO100 fabric. A first publication attempt stopped at its no-overwrite
assertion because condition-specific synthetic images reuse generated filenames.
Existing high-noise files stayed intact; condition subdirectories preserve the
distinct images. The [publication receipt](../docs/results/v95-adc-complete-quality-publication-v1.json)
has SHA256 `87e1d3578238b63cdaa22584d38cecc1a8fbd583ef89d9a680b60166e9d7cc72`.
A board attempt using the highlights metadata kind similarly wrote no output;
actual GFX highlight metadata uses the existing gfx kind. Saved recovery notes
preserve that correction. Neither correction changed image pixels or inference.

Updated the complete quality report, plan status, experiment/index links and
history explanation. The39-point/18-study plot keeps every earlier point exact
and explicitly labels V98/V99 projection. Both final4k endpoints stop without
promotion. V43 remains the working reference. The optional reviewed-ROI reader
is ready but remains disabled and has no trained quality result. Further work
stays on real quality with the V43 architecture; SOTA, broad real RawNIND
superiority and100MP/10s remain unmet.

