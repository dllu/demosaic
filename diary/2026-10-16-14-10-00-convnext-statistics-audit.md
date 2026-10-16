# Prepared the independent nine-method saved-score audit

Extended `scripts/audit_fresh_dino_statistics.py` with an explicit ConvNeXt-v58
first1000 mode, retaining the original fresh3000/10000 defaults and grid checks.
The new trial has four learned models, two calibrated RawNIND variants and
three classical methods. Photo/paired coverage and nullable support use the
required method count, and the workflow must finish all automated evaluation
before the auditor creates its output. Manual review remains separate.

Actual validation reran the completed original10k100,528 rows and336 intervals:
the complete results and input hashes equal the prior independent audit exactly,
with maximum arithmetic discrepancy1.42e-14 versus production. An actual call
against the ongoing ConvNeXt trial rejected its incomplete status before output
creation. Ruff passes; no model inference or CUDA work is involved. Private
validation receipts are under `benchmarks/dino-convnext-pyramid-audit-preparation-v1`.

Candidate source remains frozen797cfc8; this main-checkout audit script is not
part of its running model/training/evaluation imports.
