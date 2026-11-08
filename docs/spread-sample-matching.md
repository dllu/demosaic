# V174 spread sample initialization

Training is running; candidate quality is unmeasured. V173's gradient loss lowered
quiet spatial error but weakened synthetic mesh and natural fine-band response.
V174 returns to V172's unchanged seven-term criterion and tests wider initial
sampling positions in the existing matching network.

The six-input V172 EMA probe replays the existing predictions exactly. Its
coarsest matching-block sample distances stay below about 12.05 native pixels
on the selected present/absent meshes, sky and both real cab priors. Finer blocks
stay within about 2.72–5.92 pixels. These are positions reconstructed from captured
pre-tanh offsets, not the model's full receptive field or a causal measurement
of RGB influence. Convolutions and the frozen DINO parent also supply context.
[Observed offsets](results/v174-V172-offset-usage-v1.json).

The existing sampler starts from a unit 3×3 grid and adds `9*tanh(offset_CNN)`.
Its last offset-predictor weights/biases normally start at zero. V174 sets only
the bias to `atanh(7*grid/9)`, yielding a nominal grid spacing of eight feature
pixels. The residual search bound remains nine. Initial corner distances are
22.63/45.25/90.51 native pixels at the three scales, compared with
2.83/5.66/11.31 for the original initialization. The hypothesis is that starting
with separated samples makes useful repeated evidence available during training.
It is not a claim that these samples are already matched to the same structure.

Only five existing bias vectors change: 60 scalar values, with all other 183
state tensors matching the V172 initialization. The 2,088,906 trainable
parameters/141 tensors, local feature/output units, forward graph, all 96 neural
files, frozen V169 EMA/V143-DINO parent, 1,000 cached V168 rows, pair units,
criterion, AdamW/LR/clipping/EMA and schedule stay fixed. A zero output tail
retains the initial V169 prediction. Clean targets, masks and pair membership
remain training-only. Zero supplied local variance retains V169, including
ADC-only bypass; this is not a noisy-flat guarantee.

All 133 focused CPU checks pass, including ten new checks of independent NumPy
sample geometry, exact state/RNG isolation, unit-spacing equivalence, repeat
initialization rejection and invalid-parameter handling. New admission uses
three batch-4 native512 backwards and one native768 inference, four CUDA
matching calls/13 images and three discarded optimizer updates. It peaks near
6.26 GiB CUDA. Unchanged sampler/core parity and adjoint evidence are inherited
by source/library hash, not repeated. The atomic CUDA sampler gradient remains
warn-only nondeterministic; exact state restoration does not imply identical
retraining trajectories.

The same schedule completes 900 noisy updates and 100 ADC-only skips. A genuine
step-8 checkpoint must restore model/Adam/EMA/RNG and continue at step9 without
replaying a prefix. Both raw/EMA endpoints evaluate all 822 fixed cached cases,
with 1,644 exact frozen V169 replays and 144 exact ADC identities required.
V172 is the detail baseline; V173's quiet and V171's flat strengths also remain
numeric comparisons. A lower total error alone will not count as recovered detail.

Full new RGB arrays remain limited to 36 selected native cases: 72 RGB plus
72 residuals, 430,196,736 bytes. The six primary EMA offset observations reuse
existing quality forwards and additionally retain 30 pre-tanh tensors,
102,780,672 bytes. Their posthoc position audit will distinguish actual trained
sampling from nominal initialization. Other outputs stream metrics/fingerprints
and independent addition checks; no all-822 full-array posthoc audit is claimed.

The 48 boards/12 native triplets keep 160×160 crop pixels without resizing,
identical coordinates, noise and display transforms. Both protected GFX scenes,
all main sky/building/foliage/coarse-fence views, cab priors/windows and JPEGs
remain included. ISO100/AHD/JPEG references differ in capture/processing and are
qualitative, not exact GT and not scored. Captures/JPEGs/siblings remain excluded
from training. Originals stay read-only and unused; `/mnt/dataz` is not accessed.

New reserves are 49/110 GiB local/external plus a 0.5 GiB projection margin,
32 GiB runtime RAM, 52 GiB launch RAM and 24 GiB CUDA. Older guards and receipt
bytes remain unchanged. No new source/noise draws or parent/DINO calls occur.
The baseline probe adds six V172 matching calls/30 samplers separately from
candidate work. The selected, adaptively reused inputs do not establish blind
performance or training-seed uncertainty.

[Prepared sources](results/v174-spread-matching-preparation-v1.json) ·
[Runtime readiness](results/v174-runtime-readiness-v1.json).
