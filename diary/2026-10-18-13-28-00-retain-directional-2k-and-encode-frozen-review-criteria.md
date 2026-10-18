# Retain directional 2k and encode frozen review criteria

Previous turn made progress by preparing independent numerical/native review and
auditing the first checkpoint. Revalidated the actual training controller and
child by PID plus creation time. The same child remained running through the
2,000-step boundary; no restart or recipe change. The CPU watcher retained and
audited step 2,000: finite 99 model / 99 EMA / 97 AdamW states, correct counters,
shapes, initializer, manifest, LR groups and original 4k schedule. All 25,800 new
parameters have nonzero optimizer moments. Checkpoint SHA256:
`3205312b282152e56727e3a8300190a6a9038cd623bf8ca77be2597ecfdfc714`.
This is training execution evidence only; no intermediate quality score or crop
was used to alter the experiment.

Added a small standalone numerical checker implementing the previously frozen
V78/V79 criteria exactly. Each arm requires +0.05 dB known/unseen measured-CFA
and full427 rendered PSNR gains over freshly evaluated V63, each with a strictly
positive lower confidence bound; parent-relative SSIM loss must be ≤0.0001.
Matched V79-minus-V78 interval criteria remain separate: positive photo PSNR
confidence bound and known/unseen mean losses ≤0.03 dB each. Unfavorable canonical
camera-linear values are retained, with the original target-convention caveat.

The checker validates complete primary counts, unique metric/kind/role rows,
source/scene counts, matching checkpoint hashes and same fresh report/case
routes for candidates and parent/control. It checks linked file hashes once per
distinct path and rejects nonfinite/reversed confidence intervals. It does not
recompute metrics/bootstrap intervals or replace separate arithmetic/source
audits. All numerical passes still leave native/visual/full-frame review open;
automatic extension/promotion is always false.

All 17 focused tests pass in 0.05 s after correcting test-fixture arithmetic.
Tests cover exact cutoffs, rounded-looking subthreshold gains, zero bounds,
SSIM/matched-loss limits, duplicate/missing/wrong-kind/count rows, wrong hashes,
stale parent source routes and invalid intervals. Actual historical six-method
statistics parse all 15 required rows unchanged; this is explicitly historical
V76/V77/V63 preflight evidence, not a V78/V79 result. The frozen CLI also rejects
the actual live incomplete review with no output file. Ruff/format pass.

Frozen checker plan SHA256:
`3081e436db7a5f581bc30b279f7eb03cd0b7f24dda3376218d13acc1ba4a1788`.
It stores the exact future command, input criteria and checker source before
new final 4k full-panel results. It is prepared, not automatically executed on
partial data. Training, evaluator, CPU closure, working-reference supplement and
boundary watcher remain live under their exact owned identities. No model/data/
schedule/inference/metric-target/quality-gate change. No SOTA, broad real-photo
superiority, new full-frame result or sub-10-second claim. V43 remains reference;
the full objective remains active.

See [fixed numerical checker](../docs/directional-interval-numerical-criteria.md)
and its [receipts](../docs/results/directional-interval-numerical-checker-v1.json).
