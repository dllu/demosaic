# Inspect blue features directly in cached GFX RAWs

Recorded: 2026-10-22T12:13:50-07:00 (America/Los_Angeles).

The previous goal turn made progress by completing a cropped CPU RGB16 export
test and queuing the full101.996MP comparisons after the seven-panel review.
Revalidated the live V100 controller/worker and both waiting controllers before
this investigation; their frozen source/configuration inputs remain unchanged.

The larger foliage overviews showed isolated blue points outside the existing
native160 crop. Inspected the actual cached Bayer values before attributing
these features to denoising or introducing a pixel correction. At sensor
(9065,5759), the blue photosite is .326751 in DSCF3879 and .328084 in DSCF3880;
both neighborhoods have three blue sites above .1. The signal is present in
both RAWs and cannot have been created solely by V84/RawNIND inference.

A second point at (8991,5903) is .113025 in ISO6400 versus .001685 in the later
ISO100 capture. Three nearby blue sites exceed .02 in the noisy frame, versus
none in the reference. Its absence in the later frame does not distinguish
changing lights/motion from sensor/transient causes. The first-point finding
must not be generalized to both captures at the second point.

Created and actually viewed a four-panel native160 input/reference figure,
using separate Malvar demosaicing, the noisy capture's WB/matrix and +2EV for
both frames. No crop pixels are resized, warped or independently exposure-fit.
The ISO100 capture remains a qualitative reference with aperture/time/motion
differences, not GT. Selection is explicitly posthoc from a V84 CPU overview;
these are source-inspection cases, not independent model-selection examples.

[Source/pixel observations and display metadata](../docs/results/gfx-blue-feature-input-reference-v1.json)
and the figure are published on the current GFX page. The source evidence
changes the next action: retain the features and leave the processing/noise
recipe unchanged rather than treating blue points as invented restoration
artifacts. Their physical origin remains unresolved. No bad-pixel map,
filtering, new neural forward or training intervention was performed, and the
standing six-region queued protocol is unchanged. All RAW reads use the cache;
original source disks are not needed. The broader quality objective remains open.
