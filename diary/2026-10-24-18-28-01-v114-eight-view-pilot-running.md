# Measure current V114 eight-view quality on saved inputs

Recorded: 2026-10-24T18:28:01-07:00 (America/Los_Angeles).

Started a bounded CPU-only eight-view quality pilot with the newly selected
V114 checkpoint, SHA2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2.
It reuses exactly the earlier V112 pilot's24 saved observations:12 material,
two adverse M100 crops, all six standing GFX512 contexts and four previously
identified color cases. No source, ROI, noise draw, display or control output
is selected from the new results. No new RAW decoding or noise generation occurs.

The declared budget is192 new root/encoder forwards. Each identity is already
a component of its eight-view mean, so there is no extra identity-only inference.
The official Tiny identity and all91 V114 EMA tensors are checked. Weights,
input values and Torch RNG must remain exact; outputs retain every canonical
FP32 view and float64-mean-to-FP32 result. There are no optimizer updates or CUDA.
The original V116 training/evaluation/audit/comparison owners and sources remain
unchanged; V116 passed5k and continues its original20k data trial.

Copied all71 original frozen physical/helper files byte for byte. The worker
changes model labels and RAM reserves only; V112 identity-score assertions are
moved into historical observation provenance rather than incorrectly imposed
on changed V114 weights. CPU2/nice10,64GiB start/48GiB runtime available RAM,
128/96GiB internal and208GiB external reserves keep the concurrent work bounded.

The independent analyzer is queued behind the exact pilot PID/creation identity
and successful exit. It adopts the known-good V112 analysis, reconstructs all24
means, checks NumPy64/Torch64 metrics, and adds retained V112 eight-view outputs
to V104 eight-view/V114 single/eight-view/stronger RawNIND comparisons. It prepares
twelve candidate noisy/restored/exact synthetic GT triplets and matched native
material/camera/GFX/color boards. GFX ISO100 and camera AHD references remain
approximate, never exact GT. Actual native viewing follows completion.

At the recorded running snapshot the pilot has134/192 calls, with its independent analysis
waiting. This is a running experiment, not a quality gain, full427/all-camera/
all1176-color/full102MP result, timing claim or default change. All original
executed sources, controls and prior failed-analysis receipts remain intact.
Failures preserve partial work and stop without neural retries.

[Bound running experiment and source records](../docs/results/v114-dihedral8-pilot-running-v1.json).

