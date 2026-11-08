# V175 fresh-noise matching continuation

V175 tests whether a substantially longer training recipe with fresh sensor
noise can improve the weak correction learned by V172. Training is running;
quality is pending. V172 remains the balanced matching baseline, V173 the
stronger recent quiet/spatial variant, V171 the standalone-flat option, V161 the stronger learned
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

The original v1 worker stopped before its training claim and CUDA initialization
because its frozen snapshot omitted `coupled_sensor_noise.py`. Its source,
plan, launch, failure and log are preserved. A new v2 workspace includes that
dependency and passes actual frozen-worker imports, metric construction, strict
matching/full-parent/DINO CPU loads and all 54 focused tests before launch.
The earlier clipped-target rejection and a CPU binding-shape preparation error
are also retained. No successful training prefix or training-data sensor draw
was repeated.
[Preparation and exact sources](results/v175-fresh-noise-matching-preparation-v2.json) ·
[Frozen-worker readiness](results/v175-frozen-worker-readiness-v1.json).

The corrected worker passed both actual cached-parent CUDA replays, then
restored its real total-row-1008 checkpoint and continued at 1009. Independent
CPU checks of the seven saved fresh prefix batches verify unchanged targets/
calibration, noisy-intensity variance and exact common-noise pixels inside
pairs. The checkpoint contains all 141 Adam states at actual optimizer step
907 and retains all 47 frozen state tensors exactly. Partial live trace loss
totals/masks/parent argument bindings also pass. This is a running-prefix check,
not final quality evidence; no sensor noise or neural inference was repeated.
[Actual restored prefix audit](results/v175-restored-live-prefix-v1.json).

The actual row-5,000 checkpoint now has **4,500 total optimizer updates**, with
all 141 Adam states at 4,500 and all 47 frozen tensors exact. Four complete further
passes validate 4,000 rows, 3,600 loss totals, 3,588 fresh batches, 12 retained noisy
rows, 400 ADC skips and 14,376 durable events. Five visits to the first scene
have distinct actual RAW/variance/parent fingerprints with unchanged target/
calibration/pairs. This CPU-only check repeats no noise or inference and claims
no model quality. [Four-pass checkpoint/prefix audit](results/v175-four-pass-boundary-audit-v1.json).

The shared final trace auditor has also checked an actual 512-row prefix:
456 updates, 454 fresh batches, 1,820 durable parent/matching events and exact
FP32 loss totals. Eight deliberately corrupted in-memory copies of a separate
200-row prefix reject; original journals stay untouched. These check the audit
tools and partial execution, not final quality.
[Live trace audit](results/v175-continuation-trace-audit-v1.json) ·
[Auditor rejection checks](results/v175-trace-auditor-rejection-checks-v1.json).

Final postprocessing is frozen before candidate quality: nine methods,
378 table cells, 60 native figures, strict exports and browser pixel checks.
The V172 comparison uses its previously audited label-corrected view; reversing
the labels reproduces the original scores exactly. Training and its original
plan are unchanged. The larger journal/result copies and comparisons raise the
remaining local publication forecast from 0.2 to **0.4 GiB**, with the same
48/111 GiB reserves and 0.5 GiB margin; current space passes this forecast.
[Exact postprocessing sources and inputs](results/v175-postprocess-preparation-v1.json).

A local watcher now waits for the actual training owner to exit successfully,
runs the frozen final training audit, launches the fixed review once and runs
the CPU quality/offset/reduction/render stages. It stops on failures, waits
through observation errors and never restarts a scientific prefix. Its output
stops at images ready for actual viewing; it writes no visual-review claim,
human notes, final report or exports. Eight CPU owner-status checks include
PID reuse, terminal states and transient-error propagation.
[Watcher source, launch and observed live state](results/v175-completion-watch-preparation-v1.json).

## Four-pass training losses

A posthoc reduction of the already audited first four continuation passes
finds **small changes in recorded detail losses**. The table compares means
over the same clean scene rows in passes 1 and 4; these are the changing raw
model's losses before each update, not evaluations of a fixed checkpoint.
Fresh noise, model state and learning rate change together. Three noisy photo
rows retain their original observations. No inference or noise is repeated.

| Domain | Updates/pass | Pair-difference mean, pass 1 → 4 | Flat-anchor change | Total loss change | Pre-clip norm >1, pass 1 → 4 |
|---|---:|---:|---:|---:|---:|
| Mesh | 307 | 0.189039 → 0.188861 (−0.094%) | +0.071% | −0.204% | 59.61% → 46.91% |
| Weak texture | 99 | 0.247964 → 0.248109 (+0.059%) | −0.237% | −0.039% | 52.53% → 45.45% |
| Photo | 214 | 0.314902 → 0.315394 (+0.156%) | +4.797% | +0.156% | 9.81% → 9.81% |
| Flat | 141 | No pairs | −0.558% | −0.387% | 1.42% → 0.71% |
| Mixed edge/quiet | 139 | No pairs | −0.976% | −0.589% | 0% → 0% |

The flat-anchor term integrates a clean-target mask and pseudo-Huber error in
fixed 16-DN16 units. Its mean includes all image elements, so it is neither
flat-region RMS nor a sky score. Its rise on photo batches contrasts with the
fall on standalone flats; one aggregate training total cannot establish both
detail preservation and flat behavior. Reported gradient norms also differ
substantially across domains. Scalar term shares do not establish gradient or
Adam-update contributions, and batch losses mix multiple image contrasts.

The reduction checks all 3,600 FP32 totals exactly and 350 means with independent
Decimal arithmetic. It retains every pass/domain/term summary and paired-row
change counts; repeated scenes and coupled members are correlated, with no
significance or generalization claim. This is descriptive training evidence,
not a new quality result or a reason to select a checkpoint early. The fixed
training recipe continues; final raw/EMA detail, blank, quiet, flat and real
fence/sky comparisons will determine useful gains and costs.
[All reductions and exact source](results/v175-four-pass-training-loss-v1.json) ·
[Reducer](../scripts/summarize_fresh_noise_prefix.py).

## Quality and protected scenes

Both final endpoints will complete all 822 fixed cached inputs, with 1,644 exact
V169 replays and 144 ADC identities. Compare V172, V173, V174, V171 and earlier
detail strengths directly. Retain full new RGB/residual arrays for 36 native
cases and 30 offset fields from six existing primary EMA quality forwards.
Report mesh response and blank error, quiet total/spatial/DC error, native
512-flat full/coarse error and natural photographic band response/error.

The final numeric tables also include V161 EMA, the earlier stronger learned
detail option. All **822 saved outputs** use the same cached observations,
parents, ROIs and metric-source bytes as V175's fixed comparison. Rehashing and
recomputing them reproduces **8,038 old scalars exactly**, with zero inference
or new sensor draws. Its mesh response remains **5.240% of exact constructed
GT**, alongside higher quiet RMS (4.616/7.061 DN16 at ISO6400/12800) and full-flat
RMS (19.024/24.867 DN16). This preserves the stronger detail comparator and its
costs while V175 is unmeasured.
[Complete array-only baseline audit](results/v175-V161-baseline-metric-audit-v1.json).

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
