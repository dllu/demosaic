# Native-data comparison passed CPU and CUDA engineering checks

Prepared the fixed V84/V85 original20k native128/150 comparison from genuine
V63 EMA, preserving the DINO/RGB architecture and all other training factors.
CPU B1/native64/FP32 and actual CUDA B16/native256/BF16 both completed16 updates
per arm with finite91/91/89 model/EMA/AdamW states. Independent checkpoint reads
verified exact final RNG, initial shared EMA/DINO, shared-domain hashes and
actual owner exits. The CUDA native draw changed; CPU's single native draw did
not. The original CPU path-resolution failure is preserved and corrected.

Six observation-guard tests and Ruff pass. Criteria and engineering receipts
are in docs/native-data-v84-v85.md and docs/native-data-v84-v85-launch.md.
These are discarded engineering checks, not evidence of trained quality.
All44 neural/training-core files remain unchanged. No private pixels or capture
metadata enter Git. Final20k review and native crop comparisons remain required.

Commons recovery has finished both1188-source cache scales; the producer
reports1179 heuristic-clear and9 quarantined sources. The archive handoff
reconciled1188 originals and resumed the bounded background downloader. None
of those Commons arrivals enter this fixed comparison.
