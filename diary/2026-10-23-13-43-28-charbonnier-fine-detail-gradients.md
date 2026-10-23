# Measure loss smoothing on fine-detail training inputs

Recorded: 2026-10-23T13:43:28-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress: complete incoming-source QA,
the 90,864-source future corpus and its recipes were committed/pushed, followed
by the additional paired-hot-pixel feature merge. The original V104 trainer
and three dependent queues are confirmed live by exact PID/creation identity.
This turn continues quality work while that fixed20k endpoint runs.

Investigate the fixed Charbonnier epsilon.001 as a possible weak-detail
supervision limitation. Freeze twelve earlier actual clean-reader cases:
six new arrivals and all six reviewed fine-detail ROIs. Native256 targets,
additional mean-preserving contrast1/.25, three physical noise conditions,
V102 final20k CPU FP32 and epsilon.001/.0003/.0001 give72 actual restorations
and216 output-gradient checks. No optimizer or production option is added.

Two initial diagnostics fail and are preserved. The first omits required
explicit shot/read conditioning and stops before completing a restoration.
The second independently writes the same loss algebra but fails the strict
bitwise default-gradient check; a separate field fixture shows exact term
values and2.33e-10 backward differences. The successful third version calls
the actual frozen production objective, temporarily substituting only its
Charbonnier kernels for alternative epsilon values. Default terms and gradients
then replay exactly without relaxing that requirement.

The initial source bands remain above epsilon, so a declared follow-up adds
contrast.025 on the same12 sources/three conditions. This is chosen after the
first analysis and is stronger than the current.125–.5 augmentation range.
It adds36 restorations/108 gradients, for108/324 total. Nine source contexts
now have band RMS at most.001; median.000678. All108 default terms/gradients
match production exactly. Independent NumPy F64 central differences differ
by less than1.9e-10 over324 checks. All saved input/prediction tensor hashes are
independently rechecked; weights, backbone, configuration, parameter identities
and Torch RNG remain unchanged. No CUDA is initialized by the diagnostic.

At contrast.025, epsilon.0001 gives median low-noise ADC correction-slope
ratio2.180× versus default, alongside2.522× total-gradient L2. ISO100 ratios
are1.585×/2.034×, and ISO12800 ratios1.110×/1.344×. Median gradient alignment
with the target-band correction decreases in every group. This strengthens
faint-detail supervision but does not isolate it or establish trained quality.
Keep a smaller epsilon as a later matched training hypothesis; preserve the
current capacity trial's original objective. The report includes all groups,
eligibility counts, limitations and a standalone scientific PNG/SVG, actually
viewed before publication.
[Diagnostic report](../docs/loss-smoothing-detail.md) ·
[Closed execution/gradient evidence](../docs/results/charbonnier-detail-output-gradients-v1.json).

The cleaned V109 Tiny/V110 Small recipes also complete separate discarded
CUDA/native256/B16/BF16 checks, eight updates each, from the identical
V102-derived Tiny-zero initializer. Use a copied frozen source tree whose50
numerical modules match the prepared production plan, with only run/protocol
locations moved. Every initial EMA matches; frozen backbone hashes stay exact;
all91 model/EMA tensors and89 Adam states remain finite at step8. The first
real loss and all eight actual observation hashes match across arms, including
Commons/synthetic, native-RAW and paired-RAW domains. Peak allocation is
6.95GB Tiny/7.04GB Small. These overlap original V104 and another GPU user;
their timings are not throughput measurements.
[Actual CUDA closure](../docs/results/backbone-cleaned-recipes-CUDA-v1.json).

V104's original source, data and evaluation/export/detail queues remain fixed
and live. Both earlier production preparations remain unlaunched and retain
their bytes. Review the completed V104 endpoint before selecting the next
initializer; repeat affected checks if a better parent supersedes the current
V102-derived preparation. V102 remains the best completed quality baseline.
State-of-the-art fine detail, decisive broad real-camera superiority and the
100MP/10s target remain open; quality still precedes speed work.

Final verification directly compares all55 Python file hashes between the
prepared production and actual CUDA worktrees; every file matches. Thirty
distinct references in the new public receipts/figure metadata verify against
SHA256, and193 local links resolve across eight edited documentation/diary
files. The original V104 owner and all three dependent queue owners remain
live, with training at16,900/20,000 and finite recent loss. Original machine
receipts and frozen production inputs retain their bytes.

A path-specific Git whitespace attribute accepts Matplotlib's valid trailing
spaces inside the new SVG path data, preserving the exact generated bytes
already bound by the figure receipt. Other whitespace checks remain enabled.
