# V171 learned matching residual on the frozen DINO result

Training is in progress. This experiment adds a fresh 2,088,906-parameter RGB
residual above the frozen V169 EMA component and its cached V143/DINO parent.
It tests whether more matching capacity can recover weak detail, while retaining
V169 as its exact initial output. No quality gain is claimed yet.

The network reuses the pinned [NLFeMF definitions](https://github.com/MIA-UIB/nonlocal-matchfilter),
with width16 and nine learned neighbors at each of three scales. Its inputs are
the existing 39 physical RAW-innovation, noise, CFA, white-balance and parent-RGB
features. A zero-initialized 12-channel tail predicts phase-aligned RGB changes,
scaled by supplied image noise RMS. The released V170 checkpoint is not loaded:
new matching weights train from scratch on the project's existing free-image
and synthetic cache. The original 93 neural source files remain unchanged.

The fixed schedule adopts all 1,000 V168 batches: 341 mesh, 243 photo, 156 mixed,
153 flat and 107 weak-detail batches. This includes V168's finer wire/contrast
ladder. Inputs, targets, parents, noise draws and pair units are reused exactly.
The two protected GFX scenes, their JPEGs and siblings remain excluded. No
original or `/mnt/dataz` reads, new source/noise draws or parent/DINO calls are
needed.

Losses combine pixel and gradient reconstruction, paired detail differences,
paired common error, clean-flat anchoring and local/DC regret relative to V169.
Targets and pair/mask labels are training-only. The old spectral-head loss is
omitted, so architecture and objective changes are not isolated. These empirical
losses provide no noisy-flat guarantee. Zero supplied variance bypasses the new
branch exactly, retaining V169 rather than introducing V170's ADC artifacts.
ADC-only training rows skip model and optimizer updates.

The fixed run uses AdamW, learning rate0.0003, 50-step warmup, clipping1 and EMA.
A real checkpoint at step8 restores model, Adam, EMA and RNG state before
continuing at step9; no successful prefix is replayed. Final raw and EMA
endpoints are both declared before held-out inference. The sampler's upstream
CUDA input-gradient kernel uses atomic addition and explicitly reports
nondeterminism. The run retains that kernel under warn-only deterministic mode;
checkpoint restoration is exact, but a bit-exact training trajectory is not
claimed.

All 114 relevant CPU tests pass, including six new phase/routing/frozen-parent
cases. Eight independent NumPy adjoint fixtures cover CPU/CUDA, FP32/FP64 and
1×1/3×3 sampling. Full-network CPU/CUDA forward and input gradients agree within
tolerance. Synthetic batch4 native512 backward peaks at6.26GiB; native768
inference also passes. Two admission assertion/observation failures preceded
training and held-out calls; their sources, logs and actual synthetic calls are
preserved. Neither changes inference code or the trained data.

The planned review uses the same822 cached cases at both endpoints. It checks
all1,644 frozen V169 outputs against their existing fingerprints, and all144
ADC-only outputs must retain V169 exactly. All new outputs get streamed metrics,
fingerprints and independent FP32 addition checks. Full new RGB and residual
arrays are retained only for36 preselected native cases:72 RGB plus72 residuals,
430,196,736 bytes. Separate posthoc array checks will cover those36 cases; no
complete new full-array archive is planned.

The native report preserves48 boards and12 noisy/restored/exact constructed GT
triplets, with unchanged160px pixels, coordinates, noise conditioning, camera
transform, exposure and contrast. It includes main-scene sky, building, foliage
and coarse fence, plus both cab windows, noise priors and camera JPEGs. Separate
ISO100/AHD/JPEG views are qualitative references, not exact GT or pixelwise
scoring targets. Actual original-detail viewing follows completed rendering.

This bounded trial reserves52GiB local/114GiB external, plus.5GiB projection
margin,32GiB runtime RAM and24GiB CUDA. Prior guards and receipts remain unchanged.
The existing model recommendations and measured strengths remain visible until
new quality evidence is available.

[Immutable preparation and sources](results/v171-matching-residual-preparation-v1.json).
