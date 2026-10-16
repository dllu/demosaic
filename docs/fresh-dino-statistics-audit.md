# Independent check of fresh-trial score aggregation

The completed 3,000-step fresh no-context/S/B evaluation passes an independent
coverage and arithmetic check. Rebuilding its group means, source/scene means,
paired differences and bootstrap intervals from saved case scores gives a
maximum absolute difference of **1.4211e-14** from the published statistics.
[Execution, input hashes and negative checks](results/fresh-dino-statistics-audit-3k.json).

This validates the saved-score aggregation, not model inference, metric
definitions, image quality or training-repeat uncertainty. The existing
[quality report and native crops](fresh-dino-capacity-3k-review.md) remain the
evidence for that historical gate. Its model-selection decision is unchanged.

`scripts/audit_fresh_dino_statistics.py` uses standard Python arithmetic and
NumPy without importing the production aggregation functions or PyTorch. It
checks every declared method against the same observation grid, rejects
duplicates/missing cases and nonfinite core metrics, and requires optional
metric validity to match across methods for each observation. Optional
highlight/shadow metrics can be absent when their common target mask is empty;
their source-balanced means and valid-source counts are checked explicitly.

| Saved panel | Case rows | Independent aggregation | Paired comparisons |
| --- | ---: | --- | ---: |
| 427 photos + 16 procedural sources | 99,232 | Conditions/CFAs within source, then equal sources | 168 |
| Known four real scenes | 576 | Nine crops per capture, then captures per scene, then equal scenes | 84 |
| Unseen five real scenes | 720 | Nine crops per capture, then captures per scene, then equal scenes | 84 |

All eight methods cover every required observation: three learned arms,
two RawNIND gain adapters and three classical baselines. The real evaluation
stores one publisher-weight receipt for both RawNIND gain adapters; the audit
expands it into the two actual result labels. The synthetic grid has seven
conditions and all four CFA patterns. Known/unseen memberships are checked
against their hashed prepared manifests; synthetic photographs are checked
against the hashed validation manifest.

Every published group and overall mean/count is rebuilt. All **336 paired
comparisons** reproduce the current declared procedure: source/scene differences,
1,000 resamples with NumPy seed 42, and the 2.5/97.5 percentiles. This is a check of
that procedure, rather than a claim that it estimates training-seed uncertainty
or proves generalization from four/five real scenes.

Nine deliberate corruptions/invalid states were rejected: duplicate observation,
missing observation, missing primary metric, changed overall mean, changed
interval, empty interval, missing comparison, method-dependent missing optional
metric, and the still-incomplete 10,000-step workflow. The last check exits before
creating an audit result. The negative-check driver and exact auditor version
are archived beside the receipt.

Reproduce after sourcing `scripts/env.sh`:

```bash
CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 \
  uv run --no-sync python scripts/audit_fresh_dino_statistics.py \
  --steps 3000 \
  --output /mnt/external/demosaic/evaluation/fresh-statistics-3k-replay.json
```

The same command with `--steps 10000` is prepared for the original continuation.
Its complete evaluation has not yet been audited; the script currently rejects
that unfinished workflow. No CUDA work, model/data changes, original-photo
access, protected-final scoring or model promotion occurs in this audit. Ruff
passes. The running trainer and its frozen package/evaluation files are unchanged.
