# Shared-edge trial: quiet gains and weaker mesh response

Recorded: 2026-11-16T02:16:07-08:00 (America/Los_Angeles).

Completed both endpoints on all822 identical cached inputs and actually inspected
all60 comparison images/12triplets in15original-pixel sheets. Training completed
900updates/100ADCskips with all1,000row checkpoints audited. No parent inference,
new noise, protected-photo access or source changes occurred during review.

The shared-edge head has small genuine quiet/flat error gains, but reduces mesh
response: raw11.00297%→10.68557%, EMA11.10184%→10.87386%. Present-mesh full error
increases; the weaker orientation sectors in both fixed examples also fall.
EMA quiet RMS improves0.051–0.076%, cached fresh-flat RMS0.036–0.045%. Real
building green/magenta fringes, flat/quiet ripple and incomplete cab crossings
remain. Natural textures stay soft. The general recommendation remainsV120;
the new head is a retained quiet/detail tradeoff, not a decisive weak-detail win.

Published all60 native boards and small cab/building triplets with both
protected real families, two cab ROIs, nominal/fixed profiles, both JPEGs and
accurate independent-reference labels. Two exact synthetic triplets appear in
[the full report](../docs/shared-edge-comparison.md). Export hashes and complete
source/noise/ROI/display provenance are bound in the manifests.

Independently checked8,294,400new candidate display channels and20,889,600copied
noisy/baseline/reference channels. The packaged metrics reproduce510historical
V200scalars on36native cases exactly. Original machine receipts are preserved;
public gzip archives reproduce their original bytes after decompression.
The next discriminating neural check remains fresh independent-noise response
to shared-edge increments; the analytic edge-refinement result motivates richer
edge modeling but does not establish that the camera reconstruction is fixed.

