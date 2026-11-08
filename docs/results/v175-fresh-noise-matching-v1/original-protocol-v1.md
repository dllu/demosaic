# V175 fresh-noise matching continuation

V175 tests whether a substantially longer training recipe with fresh sensor
noise can improve the weak correction learned by V172. Training and quality are
pending. V172 remains the balanced matching baseline, V173 the stronger recent
quiet/spatial variant, V171 the standalone-flat option, V161 the stronger learned
mesh prototype and V120 Small the general recommendation.

The preceding [V174 experiment](spread-sample-matching.md) retained wide sample
positions without recovering crossings. Its separate six-input
[shortcut probe](results/v175-local-shortcut-diagnostic-v1.json) found a nonzero
matching contribution, while the whole added correction was only 0.20–0.22 DN16
RMS. This does not establish the cause of missing detail. The upstream
[April 2026 paper, §3.4](https://arxiv.org/html/2604.17453v1#S3.SS4) reports
1.15 million RAW-training iterations, compared with our 900-update matching
experiments. Those tasks, models and datasets differ; the budget contrast
motivates a training test rather than proving undertraining.

## Fixed continuation recipe

- Start from the actual V172 step-1000 **raw model, Adam and EMA states** with
  900 optimizer updates. Keep all 96 neural source files, the 2.09M matching
  network, local physical feature/output units, frozen V169 EMA/V143-DINO and
  all seven objective terms unchanged. No V174 spread initialization is applied.
- Make nine further passes over the same 1,000 scene/calibration/target rows:
  **8,100 new updates, 900 ADC skips and 32,400 images**. Including V172, this is
  9,000 total updates/36,000 images on 1,000 unique scene batches. It does not
  introduce new photographic sources, synthetic geometry or camera transforms.
- The full CPU preflight checks all input fingerprints and reconstructs Bayer
  samples independently in NumPy. **897 noisy rows per pass** reproduce original
  clean sensor hashes or verify inactive reference-white clipping. Generate a
  fresh stateless CPU sensor seed for each visit, with shared Poisson counts/read
  noise inside the existing counterfactual pairs. Derive variance from the new
  noisy intensity. Targets, masks and pair units stay training-only.
- **Three clipped photo rows, steps 65/358/543**, cannot reproduce their original
  sensor signal from the stored target. Retain their exact old noisy arrays and
  matching cached parents. The first preflight rejected this assumption before
  any new noise or neural call; its source and log are preserved. No target is
  silently substituted for a clipped physical signal.
- Thus **8,073 fresh batches** recompute their exact frozen V143/DINO parents;
  **27 noisy batches** reuse their original observations/parents. ADC rows skip
  sensor draws, parent, matching and optimizer work. Two cached native-size
  parent replays must match their saved fingerprints before training begins.
- Reheat learning rate to 0.0001 with a 100-row warmup and cosine decay to
  0.00001. Keep AdamW, clipping and EMA rules. Save checkpoints at total row
  1008/2000/5000/10000; actually restore model/Adam/EMA/CPU+CUDA RNG at 1008 and
  continue at 1009 without replay. Only the final raw/EMA endpoints receive the
  fixed quality comparison. Budget, noise realizations and learning-rate
  schedule change together; their individual effects are not isolated.

Global RNG stays unchanged because noise uses local seeded generators. Atomic
sampler input gradients retain the inherited warn-only nondeterminism; exact
state restoration does not promise a bit-exact retraining trajectory. The
first eight continuation rows retain actual fresh inputs and parent arrays for
independent checks; later rows retain seeds, fingerprints, observed parent
arguments, losses and durable call records, rather than a full array archive.

The new run reserves 48/111 GiB local/external, plus a 0.5 GiB projection margin
and projected remaining bounds of 0.2/1.25 GiB. Runtime/launch RAM remain
32/52 GiB and CUDA quota 24 GiB. Older guards and receipts are unchanged.
The model graph/library/native-backward admission are inherited unchanged;
no new matching admission forwards or discarded optimizer updates are planned.
The current focused CPU selection passes 54 checks, including 18 new tests for
fresh realizations, physical moments, paired cancellation, CFA sampling,
variance conditioning, seed uniqueness and rejection before sensor draws.

## Quality and protected scenes

Both final endpoints will complete all 822 fixed cached inputs, with 1,644 exact
V169 replays and 144 ADC identities. Compare V172, V173, V174, V171 and earlier
detail strengths directly. Retain full new RGB/residual arrays for 36 native
cases and 30 offset fields from six existing primary EMA quality forwards.
Report mesh response and blank error, quiet total/spatial/DC error, native
512-flat full/coarse error and natural photographic band response/error.

Render and actually review 60 fixed native figures, including 12 noisy/restored/
exact constructed GT triplets. Preserve identical 160×160 pixels, coordinates
and display transforms; record source/ROI, hashes, physical noise and exposure.
Keep a native-pixel browser viewer and verify its displayed crops.

Main DSCF3879 ISO6400/DSCF3880 ISO100 covers sky, building, foliage and coarse
fence. Extra DSCF3842/3835 covers both fine cab windows, both priors and both
camera JPEGs. Their aperture, depth of field, shutter, motion and processing
differ; ISO100/AHD/JPEG images are qualitative references, not exact GT or
pixelwise scoring targets. Both capture families/JPEGs/siblings remain excluded
from training. Originals stay read-only and unused; `/mnt/dataz` is unavailable
and will not be accessed.

No improvement, blind generalization, noisy-flat guarantee or new full-frame
timing is claimed before the completed comparisons.
