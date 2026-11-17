# Disjoint RAW guides and the long run’s first corpus epoch

Recorded: 2026-11-17T10:55:06-08:00 (America/Los_Angeles).

The previous turn made progress by closing the camera and full color panels and
launching the larger faint-detail study. This turn tests the contextual geometry
hypothesis with delivered reconstructions, verifies the long run’s first
corpus epoch and measures a bounded CUDA evaluation replay.

The [direction-guide report](../docs/scene-wave-guides.md) compares query-only,
matching and unrelated guides on eight reused procedural geometries. Each query
fits its own phase, RGB amplitude and nuisance edge on disjoint CFA folds. The
16 donor simulations have independent noise, shifted phase and stronger wires.
Initial bounded donor fitting found both true frequencies in 1 of 16 regions.
Full-frame edge fitting on the exact same donor RAW finds both in 14 of 16.
All 96 query-only outputs reproduce bit for bit. The four original-source
unguided replays also match code frozen before this change.

At ISO400 away from the edge, matching guidance raises projected weak response
from 2.751% to 4.184% and lowers weak-increment RMS on all eight geometries.
Compared with V143, the improvement in that RMS is 0.0081 DN16. Near-edge RMS
slightly worsens and ISO6400 weak results barely move. Measures include
quiet RMS and projection in roles lacking the weak wire. Both versions have
128 independently audited metric rows. All eight synthetic boards were opened,
and the eight triplets share exact native pixels with their boards.

Both standing GFX families were also tested with disjoint same-capture donor
ROIs over V120. The coarse-fence guide leaves overcast sky exactly unchanged,
with small building and foliage corrections. Cab left gains diagonal modulation
and cab right loses some query-only stripes. Fine crossings remain unresolved
at both profiles. All eight real boards were opened, with 32 noisy, V120,
AHD and JPEG display panels exact to the closed native review. The ISO100
references are qualitative. Both capture families remain outside training.
No original RAW opens or learned forwards were needed for these comparisons.

The first focused test run caught an uninitialized harmonic split in the guide
path. It also lacked the scripts path for existing test imports. Both issues
were corrected before collection. The executed sources and both test logs are
preserved. The final local-wave run passes 69 tests and Ruff.

The [CUDA probe](../docs/local-primary-cuda-probe.md) checks 24 matched V120 and
Corpus20k EMA model batches using the original 0.25 maximum and 0.025 RMS DN16
limits. The observed maxima are 0.249996 and 0.022297 DN16. Maximum primary
score change is 4.48e-6 dB. Summed recorded forwards take 377.897 CPU seconds
and 36.670 CUDA seconds. These timings are from concurrent sessions and CUDA
uses channels-last FP32. Peak reserved CUDA memory is 3.752 GiB under the
4 GiB cap. The previous scene highlight failure remains historical evidence.
The CPU panel workers continue their original numerical protocols.

The [long-run first-epoch audit](../docs/results/scene-wave-guides-v1/long100k-first-epoch.json)
verifies 90,778 distinct ordinary sources by update 17,039. It checks 276,000
slots through 17,250 and confirms 92,049 ordinary visits plus 4,847 reviewed
visits. All source/crop records and 69 actual conditioning chunks match the
control prefix apart from the correctly distinct order-header identity. At the
live checkpoint, training had advanced through 17,875. An owned CPU worker
waits for the immutable long-schedule 20k receipt, then compares the existing
110 native inputs against fresh V120 and short-schedule20k controls.

Both broad CPU photo collections and the larger faint study remain live at
392/3,162, 597/3,162 and 110/428 batches. The available local synthetic gain
and real-crop tradeoff do not establish general fine-detail recovery. V120
remains recommended. Full comparables and the long training trajectory continue.
