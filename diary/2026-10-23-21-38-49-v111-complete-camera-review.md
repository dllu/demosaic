# Complete V111 development camera panels

Recorded: 2026-10-23T21:38:49-07:00 (America/Los_Angeles).

Completed V111's entire original camera development grid on CPU while V112
continues its fixed20k training. All72 known and90 unseen native512 inputs
match the earlier comparison's fingerprints exactly. Original448 scoring
interiors, case noise profiles and measured-CFA references remain unchanged.
Only the fixed final V111 endpoint is used; no RAW source is decoded and the
protected16-scene reserve is unscored. The worker exited successfully.

Four actual V104 nativeB1 CPU replays reproduce earlier B2 CPU floats exactly;
their primary PSNR agrees with original GPU scores within.00000763dB. The full
study adds162 V111 forwards and these4 parent checks, with no additional
reference inference or training. V102/V104 GPU and stronger RawNIND-preup CPU
controls are reused. New NumPy64 primary/AHD-rendered PSNR and chroma/gradient
checks cover all162 new rows, maximum PSNR difference below.000005dB.
Six original control means reproduce exactly after balancing9 crops/capture,
2 captures/scene, then4/5 scenes.

| Method | Known CFA PSNR | Unseen CFA PSNR |
| --- | ---: | ---: |
| V102 |54.23709|53.97177|
| V104 |54.26606|53.91700|
| V111 |54.25270|53.93706|
| RawNIND-preup |54.26068|53.86528|

V111−V104 is−.01336dB known, source-bootstrap95% interval[−.02103,+.00130],
1/4 scenes improving;+.02006dB unseen,[+.00869,+.03304],5/5 improving.
V102 remains higher on unseen. V111 versus RawNIND-preup is−.00797/+.07178dB,
with both intervals crossing zero. These are finite development-scene
intervals, not training-seed/general-camera evidence; external training
membership remains unproven.

All12 original parent-adverse native160 cells were viewed. V111/V104 still
have broad spatial/color blotches; RawNIND-preup is smoother and scores higher
on both selected fields. Coulicoco's selected448 crop declines.03164dB versus
V104; top_of_Expedit rises.21219dB, but both remain below the stronger reference.
This local regression is retained alongside all5 unseen scene means improving.
AHD RGB is auxiliary, not exact GT. No new ROI selection follows V111 outputs.

[Complete camera evidence](../docs/results/v111-camera-complete-v1.json) and
[current material/camera/GFX report](../docs/v111-early-quality.md) preserve useful
material gains and real-camera limitations together. The existing two synthetic
noisy/restored/exact-GT examples remain in the README and report. Broad photo,
color, weak-detail and full-frame results await the unchanged V112 queues.

The version plot now adds V111's two completed camera points, with its full427
photo score absent. The previous JSON/CSV keep their original paths/bytes;
prior current PNG/SVG/PDF bytes are archived in the through-V104 snapshot.
A separate current derived registry drives future rebuilds. Eight focused
history tests verify pending/invalid scores cannot become measurements.
The initial camera-only plot draft counted45 total versions in the photo title;
its executed source/PNG are archived and the corrected title states44 completed
photo endpoints. No experiment receipts, fixed plans or selector bytes change.
The final plot verification binds versioned registry/CSV/figure/source/selector
snapshots; mutable current views can advance without losing this publication's
exact bytes. Initial verification output that pointed directly at current
views is preserved privately alongside the corrected snapshot-bound receipt.

Current documentation now reflects the completed camera panels and ongoing
V112 training. These results do not establish broad real-photo superiority,
SOTA or the100MP/10s target; quality work remains active.

