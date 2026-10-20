# Original20k native-data training completed

At 2026-10-19 19:50 UTC both V84/V85 arms had completed their original 20,000
updates, and the exact trainer and controller owners had exited. The queued
review then independently read both genuine final checkpoints and passed its
boundary check before starting the known/unseen panels. No retry, extension,
interim selection, architecture change or promotion occurred.

The final checkpoint SHA256s are
`134887e12357aabf420cceee3ee53fc8832cf02a8f81ff883b829a9e51e16f10`
(control) and
`44d46580d1026f8581e4a9404dbd7c3eed9721459cf19edd1efecdc266594c57`
(expanded). The final retained copies match their closed `last.pt` bytes. Each
has finite 91-model/91-EMA/89-AdamW states with optimizer counters 20000. The
review verifies final Python/CPU/CUDA RNG equality and source archives differing
only in the native manifest. All 595 recorded shared input pairs match; all
221 recorded native pairs change. Each arm has 801 finite logged training rows
and the exact original20k learning rates, ending at approximately 1e-6 with the
declared 10% floor. Unrecorded examples were not independently replayed.

The read-only collector in
`.cache/benchmarks/native-data-original20000-completion-v1/` rehashes final model,
retained-copy, result, metrics, observations and independent-boundary bytes.
Its first two attempts stopped before writing a receipt: one assumed selector
and training-log domain names were identical, and one associated floating-point
LR operations differently from the trainer. Both failed scripts and observations
are retained. The completed collector maps the declared domain names and
computes progress before multiplying by pi, preserving exact LR equality.
Neither failure changed training, checkpoint or review state; no CUDA was used
by the collector.

The public receipt is
[`docs/results/native-data-original20000-completion-v1.json`](../docs/results/native-data-original20000-completion-v1.json).
Full held-out quality, analytic/color/highlight checks and actual native viewing
are still pending. This is integrity evidence, with no quality, detail, speed,
full-frame eligibility or promotion claim. The README remains on V43.
