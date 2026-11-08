# V175 first full continuation pass

Recorded: 2026-11-07T18:30:39-08:00 (America/Los_Angeles).

V175 completed the first full continuation pass without a restart: 900 new
updates, 897 fresh sensor batches, three retained clipped-photo observations
and 100 ADC skips. The actual total-row-2000 checkpoint contains all 141 Adam
states at optimizer step1800, including900 inherited V172 updates. All47 frozen
state tensors retain their initial values. Strict raw/EMA loads and finite
optimizer checks pass on CPU without any neural inference.

The first repeated scene at continuation row1001 has the same target,
calibration and pair fingerprints as row1, but a different stateless seed,
actual noisy RAW fingerprint, supplied-variance fingerprint and newly computed
frozen-parent fingerprint. This verifies an actual cross-pass fresh
realization, rather than only unique planned seed numbers. Second-pass arrays
were streamed and are not independently reconstructed here.

The shared final auditor also checks all1,014 complete rows/events observed
at the audit timestamp, including exact FP32 weighted totals and inherited
clean masks. Journal-prefix lengths/hashes bind those records. The original
trainer PID274124/create1794102724.04 and watcher PID287357/create1794104682.2
were directly confirmed live. The watcher is correctly still waiting for the
whole training run, not treating a mid-run checkpoint as phase completion.

These checks regenerate no sensor noise and repeat no model/parent/DINO/sampler
forward. Training and final quality remain incomplete; no image-quality gain
is claimed. Keep V172 as the balanced matching baseline while the longer
recipe completes. `/mnt/dataz` and originals remain unused.

[Actual checkpoint and cross-pass audit](../docs/results/v175-first-pass-boundary-audit-v1.json) ·
[Protocol/status](../docs/fresh-noise-matching.md) ·
[Completion watcher](../docs/results/v175-completion-watch-preparation-v1.json) ·
[Prepared final comparisons](../docs/results/v175-postprocess-preparation-v1.json).
