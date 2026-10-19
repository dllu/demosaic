# Diagnose the bank ADC detail deficit at fixed weights

Executed a separate read-only inference-component diagnosis of the closed
V80/V81 original4000 checkpoints. Preserved their completed review, training
budgets, frozen observations, default and eligibility decisions. No new training
or candidate checkpoint was produced.

The first CPU64 hook/state preflight passed. The first CUDA setup failed before
inference because set_per_process_memory_fraction received an unindexed CUDA
device. Archived that exact source/plan/failure in diagnostic-v1. Corrected only
device indexing and normalized output-path checks in diagnostic-v2, froze236
files, passed a fresh CPU64 preflight, then executed the complete native256
CUDA FP32 diagnostic. The successful CUDA owner session86553 exited0.

All448 original observations were reused across five modes, yielding2240 rows:
full/base for both models and final-module bank-output-zero replay for V81.
Capturing the final-module input preserves the trunk's return-features path.
Bank-zero executes the real module then replaces only its output. Every full
branch replay is bitwise exact, all original896 full-model metric rows match
within the predeclared tolerances, observation hashes match between models, and
complete model/DINO tensor hashes remain unchanged. Hooks are removed after use.

ADC-only level.01/contrast.02/period4 control/base gain.80325060 versus bank/base
.46710520 already contains the loss. Full outputs are.79645993/.46707526;
zeroing bank logits gives.46639836, a slight worsening. Conditional bank gain
is+.00067690. The failing inputs have zero bank clipping despite the ADC
variance floor being active. These findings locate the current forward-path
deficit, without proving which optimization path caused the different bases.

At the two original high-noise weak carriers, conditional bank gain contributions
are+.00170308/+.00149179, while full matched gains still fail the original+.05
requirements. Across all24 carriers the contribution is mixed. All four flat
groups, other metrics, quadrature/ranges and paired metric differences remain
in the complete public result. No new photographic quality claim or crop set is
needed for this fixed-weight diagnosis; the existing full review retains exact
GT and GFX native crops with their original metadata.

Added independent CPU-only scalar/source auditor:2240 unique rows,140 complete
groups,3760 summary scalars (maximum arithmetic error2.220446049250313e-16),
896 baseline replays,236 frozen files, input/checkpoint/source hashes and both
preflight/diagnostic bindings. It does not re-infer model tensors. The new report
is docs/directional-bank-component-diagnostic.md and complete public result is
docs/results/directional-bank-component-diagnostic-v1.json. Next useful work is
a bounded gradient-path investigation, before a separately predeclared training
study. No private-native extension activation, HDD reads, full-frame trial,
protected-final scoring or promotion occurred. Global PROMPT goals remain open.
