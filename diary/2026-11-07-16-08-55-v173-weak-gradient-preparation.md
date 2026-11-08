# V173 amplitude-balanced gradient preparation

Recorded: 2026-11-07T16:08:55-08:00 (America/Los_Angeles).


The previous goal turn made verified progress: V172 training/822-case quality,
60 actual native views, exact controls, selected-array audits, documentation and
push completed. Its local input/output units largely remove V171 color damage
but still miss the requested real crossings. The goal remains active.

The selected ten-batch training inspection shows modest global/local unit
ratios, but 69/97% of nonzero target gradient components in two mesh batches lie
below the existing gradient transition. This measures clean amplitudes, not
actual residuals or a causal attribution. It motivates changing weak-gradient
supervision rather than only pixel loss units. Earlier V141 reduced an epsilon
on a different architecture and gained modest faint ADC accuracy, without new
mesh recovery; this is a different normalized gradient objective and ADC bypass.

V173 keeps all 96 neural files, the V172 initialization, frozen V169/DINO,
V168 1,000-row cache, pair units and AdamW/LR/EMA schedule. Only gradient
supervision changes: physical error derivatives use detached clean-gradient
RGB RMS rounded by 2 DN16 and unit-transition pseudo-Huber, coefficient 0.25.
Weak/zero target gradients receive the largest weights. Six other terms and
masks match by independent tests and AST checks. No target enters inference.
Amplitude units and smoothing transition change jointly; no individual-factor
claim. This does not establish hallucination-free noisy flats.

All 162 focused CPU checks pass, including 13 new independent NumPy values/
analytic derivatives, weak/flat descent, constant-error behavior and isolation.
Native admission uses four CUDA matching/frozen calls, 13 images, three discarded
updates and three NumPy checks of actual CUDA criterion values, peak 6.26 GiB.
Unchanged sampler/core primitive evidence is inherited, not repeated or counted
as new. Atomic CUDA sampler gradients remain warn-only nondeterministic.

The first preparer failed a strict AST check because Ruff moved the criterion
import after model_hash. Two unlaunched follow-ups then found no plan. No worker
or scientific prefix ran. Original work/source/log and empty checkpoint/native
directories are preserved. The corrected comparison allows only that import
substitution/order; work-v2 is the successful freeze. Initial module/network
hashes match V172, all other numerical training statements match, and the metric
frontend plus actual endpoint/renderer labels pass before training launch.

Training owner 145153/create1794096654.5 launched the fixed schedule. Expected
900 updates/100 ADC skips with actual step-8 restoration; quality remains pending.
Both raw/EMA endpoints/all822 cases and 60 native views stay fixed. New storage
reserves 50/112 GiB plus0.5 GiB margin are declared; older guards unchanged.
No original/dataz reads, new source/noise draws or parent/DINO calls. Protected
scene families stay out of training, originals read-only and real references
qualitative, not exact GT.

[Protocol](../docs/weak-gradient-matching.md) ·
[Preparation](../docs/results/v173-weak-gradient-matching-preparation-v1.json) ·
[Readiness](../docs/results/v173-runtime-readiness-v1.json) ·
[Preserved attempt](../docs/results/v173-preparation-failure-v1.json).
