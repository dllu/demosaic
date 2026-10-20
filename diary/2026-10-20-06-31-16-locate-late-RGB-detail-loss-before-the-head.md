# Locate late RGB detail loss before the head

The previous turn made progress by closing the V90/V91 quality and legacy
physics-batching reviews. This turn used those actual failures to separate
the immediate head effect from adaptation in the earlier shared path. The
older ADC projection study was checked first; it already addresses noiseless
inputs only and does not explain noisy detail loss. No old experiment or
training budget was repeated/extended.

New guarded diagnostic tools observe an actual full forward, capture the
head inputs and physical offset/span, and replay the identical inverse.
Both complete physical RGB and direct-head replays must be exact. Reuse
the same decoder/physical/DINO fields for bypass/pooling; no extra common
network passes. Targets are excluded from forward arguments. Frozen pooling
of V91 is not a retrained global model, and the bypass is not a model trained
without the head. Common CNN/adapters/earlier guidance remain jointly adapted.

The new nine tests plus19 existing head tests pass:28 tests,87.02s; Ruff
passes. Genuine CPU preflight loads V63/V90/V91 and executes six64×80 cases,
12 common forwards, all exact replay/state/parameter/RNG checks, no CUDA.
Plan SHA256 `812d2a21780e4966ac4a6787e75089c056340b18a9db9dee23caae88f6bb7aa0`;
CPU proof `91a4c21caaa52e103854ba43569b7afe2848d7c8a70b78cb942304a03a6d5dfb`.

The resource-bounded detached controller1210311/create1792501614.25 waits
for48GiB stable60s, then starts worker1210851/create1792501675.87. Both exit
successfully. Actual GPU data: all12 ADC groups with four unique CFAs, not
four duplicate draw labels; two noisy carriers and a flat with16 original
CFA/draw observations each. Total96 observations / six methods /576 metric
rows. Capture costs75 common forwards including three unhooked parity controls;
variants reuse existing features. All47 model modules equal the actual old
training archive. All full/tail/head replays are exact; weights/parameter
identities/input hashes/CPU-CUDA RNG remain unchanged. All DINO hashes match
the official prior state370a84…540fd, and all five captured B4 measurement/
DINO/offset/span fields match between arms. Ten complete head-input batches
and original strides remain cached, avoiding future common-network reruns.

All32 native cells /24 triplets are actually viewed before new component
statistics. ROI160, native256, RGGB/draw0. Fixed dark display16× and bright1×
is shared across methods/noisy/exact analytic GT. No resizing or new photo/
GFX inference occurs. Manual record SHA256
`98bb3e96e27d85800cc56a0784d60817f41e71840d1a42fed7ce111eb7abe75a`.

The main dark4px ADC difference is−.11314567: pre-head−.11314546 and direct
late-head−2.10e−7. The bright difference is−.05411034: pre-head−.05411798,
late+.00000764. Pooling V91 changes only+.00001415/+.00000767. Parent gains
.752261/.787508 exceed both adapted outputs; dark noisy carriers remain
nearly absent even before the head. Immediate bypass/pooling therefore does
not recover these losses. Training-gradient causation is not ruled out.

All original full-checkpoint metrics replay within the predeclared1e−6 gain /
1e−8 error limits: gain-family max1.85e−7. Independent NumPy FP64 RGB accounting
is exact; a separate explicit least-squares fit of actual RGB differences
checks80 carrier observations/320 component fields within7.40e−15. All12 ADC
groups, noisy cases/flat and all90 method/signal group means remain public.
Final diagnosis SHA256
`7eb25e061bbf73aade53adeb08b9331abbd4304e5272a61c7e2349f2cd6806d5`.

Report: `docs/late-rgb-component-review.md`; fixed protocol:
`docs/late-rgb-detail-decomposition.md`; public evidence uses the prefix
`docs/results/late-rgb-components-`. All25 native PNGs are copied exactly.
The full data/source/captures remain at
`/mnt/external/demosaic/experiments/late-rgb-detail-components-v1/`.
Final publication checks bind current scripts/tests to actual frozen copies.

The next training question is whether protecting the mature shared path while
learning refinement avoids these losses. Freezing would require common model
AND EMA tensors kept exact; no such trained improvement is claimed here.
No new checkpoint/default/README/promotion changes. Originals/source drives
remain untouched; only generated analytic SSD data are used. External free
space509.16GiB and RAM62.9GiB at the final measurement. SOTA/native superiority
and100MP/10s remain unmet/unproven; the full goal stays active.
