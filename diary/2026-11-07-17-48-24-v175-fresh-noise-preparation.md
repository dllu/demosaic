# V175 fresh-noise continuation preparation

Recorded: 2026-11-07T17:48:24-08:00 (America/Los_Angeles).

The previous goal turn made progress: V174 completed training, both endpoints,
822 cases, 60 native views, exports and publication. It retained wide positions
without useful crossing recovery. Its separate shortcut probe found a nonzero
matching contribution but only a small whole correction. The full detail/flat
goal remains open.

V175 tests a longer training recipe with new sensor realizations. The upstream
[April 2026 paper, §3.4](https://arxiv.org/html/2604.17453v1#S3.SS4) reports
1.15 million RAW-training iterations; our matching trials used 900 updates.
Different tasks/models/data prevent treating that contrast as proof of
undertraining. Start from the actual V172 raw model, Adam and EMA states at
900 updates; keep all 96 neural sources, local units, frozen V169/V143-DINO and
all seven loss terms. Make nine more passes with a 100-row LR warmup to 1e-4
and cosine decay to 1e-5. Budget, noise realizations and LR change jointly.

The full 1,000-row CPU preflight checks input fingerprints, independently
samples Bayer phases and verifies retained pair units. Exactly 897/900 noisy
rows admit re-noising of the original clean sensor. Photo rows 65/358/543 have
clipped targets whose stored RGB cannot recover the original signal; retain
their exact cached observations/parents. Thus nine passes plan 8,073 fresh
sensor batches with newly computed V143/DINO parents, 27 cached noisy batches,
900 ADC skips and 8,100 additional updates/32,400 images. Total updates become
9,000 including V172. There are still 1,000 unique scene/calibration/target
batches, with no new source/geometry/camera construction.

The first CPU preflight rejected the invalid all-targets-as-clean assumption
before noise/neural calls; source and log are preserved. A subsequent CPU
preparation error compared a descriptive `step` field with a path/hash-only
binding; its bytes are also retained. The original v1 worker then exited before
`train.claim` or CUDA runtime because its frozen workspace lacked
`coupled_sensor_noise.py`. Authoritative PID inspection confirmed it terminal,
with zero sensor draws, neural forwards or optimizer updates. Keep the complete
v1 workspace, plan, preparation receipt, launch, failure and log.

A new **V175-fresh-noise-matching-v2** workspace adds the missing dependency.
Before launching it, actual frozen-worker imports, metric construction, strict
matching/full-parent/DINO CPU loads and all 54 focused tests pass. Eighteen new
tests cover seeded fresh realizations, physical moments, phase sampling,
unchanged target/calibration, pair common-noise cancellation, variance, seed
uniqueness and rejection before sensor draws. The graph/native sampler
admission inherits unchanged V172 proofs rather than repeating CUDA calls.

The corrected worker, PID274124/create1794102724.04, passed both actual cached
parent replays at different native sizes before training. Its real total-row
1008 checkpoint restores model/Adam/EMA/CPU+CUDA RNG exactly and continues at
1009 without replay. Independent CPU checks verify seven saved fresh batches,
their parent fingerprints, physical variance and common-noise equality. All
141 Adam states are at actual step907; all47 frozen tensors match the initial
state. Live prefix loss totals, inherited clean masks and observed parent
argument fingerprints pass. That partial audit is timestamped; it does not
stand in for later authoritative owner/process checks or final quality.

This run reserves 48/111 GiB local/external plus projected remaining bounds and
0.5 GiB margin, RAM32/runtime and52/launch, CUDA24. Prior guards stay unchanged.
Two final endpoints/all822 cached quality cases, 36 full-array native cases,
30 offset captures from six existing EMA forwards, 60 native figures/12 triplets
and both protected GFX scenes/priors/windows/JPEGs remain fixed. No original or
`/mnt/dataz` reads. Real references remain qualitative rather than exact GT.
V172 remains the balanced matching baseline while training and quality finish.

[Protocol and current status](../docs/fresh-noise-matching.md) ·
[v2 preparation](../docs/results/v175-fresh-noise-matching-preparation-v2.json) ·
[Preserved v1 preparation](../docs/results/v175-fresh-noise-matching-preparation-v1.json) ·
[Frozen-worker CPU readiness](../docs/results/v175-frozen-worker-readiness-v1.json) ·
[Actual restored live-prefix audit](../docs/results/v175-restored-live-prefix-v1.json).
