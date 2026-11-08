# V173 amplitude-balanced gradient matching

Training is running; quality is unmeasured. V172's local input/output units
largely remove V171's added quiet-color cast, but weak crossings remain missing.
This trial changes only the gradient term of the V172 training objective.
The network, seeded initialization, cached inputs, frozen V169/DINO component,
pair units, optimizer and schedule stay fixed.

For each horizontal or vertical edge, let `g` be the clean RGB target gradient,
`d` the gradient of output-minus-target, and `f = 2/65535`. The new term averages
`rho(d / sqrt(mean_RGB(g²) + f²))`, where `rho(z) = sqrt(1+z²) - 1` is evaluated
without small-error cancellation. Its coefficient remains 0.25. The old term
used an image-wide noise unit and a Charbonnier transition of 0.003. Local
amplitude units and a unit pseudo-Huber transition change together; their
individual effects are not isolated.

Weak and zero target gradients receive the largest weights. False gradients in
a clean flat target are penalized against zero; targets are never replaced with
constants. Physical derivatives precede normalization, so spatially changing
units do not invent a derivative of a constant RGB error. Clean gradients and
weights enter only the training loss. The inference graph is exactly V172's;
no target, pair label or clean mask enters inference. This empirical objective
does not establish noisy-flat safety.

A preselected inspection of the first two positive-shot cached batches in each
of five domains covers ten batches/40 images. In the two mesh batches, 69% and
97% of nonzero clean gradient components fall below the old gradient transition.
These are target amplitudes, not actual gradient residuals or evidence of a
causal training failure. Global/local noise-unit differences are usually modest
in the same selected material. [Unit inspection](results/v173-training-unit-inspection-v1.json) ·
[Gradient inspection](results/v173-training-gradient-inspection-v1.json).

All six other loss terms, their coefficients and clean-flat masks are unchanged:
pixel reconstruction, local/DC regret, flat anchoring, pair difference and pair
common error. AST checks verify this isolation. The training loop differs only
in its criterion import and formatter ordering; model construction, runtime,
resource handling and exact restoration logic match V172. All 96 neural source
files remain unchanged. The new criterion does not load released V170 weights.

All 162 focused CPU checks pass, including 13 new independent NumPy value and
analytic derivative checks, descent toward faint targets/away from false flat
texture, changing-unit constant-error behavior and six-term/mask isolation.
New native admission uses three batch-4 512-pixel backwards and one 768-pixel
inference, with three independent NumPy checks of the actual CUDA gradient-loss
value. It adds four matching calls/13 images and three discarded optimizer
updates, peaking at 6.26 GiB CUDA. Unchanged primitive/core parity and adjoint
evidence are inherited by source/library hash; those calls are not repeated.
The atomic CUDA sampler gradient remains nondeterministic.

The fixed 1,000-row V168 schedule contains 900 noisy updates and 100 ADC-only
skips. A genuine step-8 checkpoint must restore model, Adam, EMA and RNG state
and continue at step 9 without replay. Both raw/EMA endpoints and all 822 cached
quality cases are fixed before inference. They must replay 1,644 frozen V169
outputs and retain V169 exactly on 144 ADC controls. V172 EMA and V169 EMA are
both numeric baselines. There are no new source/noise draws, parent/DINO calls
or original/dataz reads.

Only 36 preselected native cases retain full new arrays: 72 RGB plus 72 residuals,
430,196,736 bytes. Other outputs receive streamed metrics/fingerprints and
independent in-process addition checks. Independent posthoc array checks will
cover those selected cases; no full-array audit of all 822 cases is promised.
The same 48 boards/12 native noisy-restored-GT triplets retain 160-pixel crops
without resizing, identical coordinates, conditioning and display transforms.
Both protected GFX scenes, cab priors/windows and camera JPEGs remain included.
ISO100/AHD/JPEG references are qualitative, not exact GT and not scored. Their
captures, JPEGs and siblings remain excluded from training and originals read-only.

This trial declares 50/112 GiB local/external reserves plus a 0.5 GiB projection
margin, 32 GiB runtime RAM, 52 GiB launch RAM and 24 GiB CUDA. Existing guards and
receipts stay unchanged. An initial preparation attempt rejected only import
ordering; it created no plan or worker. That source/log and empty output
directories are preserved; `work-v2` contains the successful freeze. The metric
frontend and endpoint/panel labels are checked before training launch.

[Prepared sources](results/v173-weak-gradient-matching-preparation-v1.json) ·
[Runtime readiness](results/v173-runtime-readiness-v1.json) ·
[Preserved preparation failure](results/v173-preparation-failure-v1.json).
