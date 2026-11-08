# Bounded coherent pair-response supervision

**V183 has passed real CUDA updates/restoration and is training; quality is unmeasured.**
The [V182 gradient study](flat-spatial-gradient-conflict.md) finds that added
spatial pressure can oppose weak-detail response through shared parameters.
This follow-up adds direct coherent response supervision while retaining all
eight V181 terms, their FP32 total order and the existing clean mask. The
architecture and all 98 neural source files stay unchanged. V180/V181's
[completed quality comparison](flat-spatial-evidence-comparison.md) remains
the current model evidence.

[Loss implementation](../scripts/coherent_pair_objective.py) ·
[Independent formulas and tests](../tests/test_coherent_pair_objective.py) ·
[Native saved-output replay](../scripts/replay_coherent_pair_gradients.py) ·
[Exact CPU sources and evidence](results/v183-coherent-pair-CPU-preparation-v1.json).

For each disjoint training pair, subtract the two actual camera-RGB targets
and remove each channel's spatial mean, giving template t. Center the restored
pair-difference error in the same way. The scalar residual is

```text
r = mean(centered_pair_error × t) / (mean(t²) + (1/65535)²)
loss_pair = sqrt(1 + r²) − 1
```

The term averages pairs equally, using FP64 reductions and a stable pseudo-Huber
formula. It enters at **0.25 × the existing domain weight** after the unchanged
eight-term FP32 total. A 1-DN16 RMS energy floor bounds sensitivity as clean
differences vanish, without an amplitude cutoff. Constant target offsets
and constant pair-color errors are removed independently per channel. Targets,
pair membership and these reductions enter only after inference.

This encourages coherent target response instead of changing every local
gradient weight. It also has clear blind directions: errors orthogonal to the
template and pair-color offsets receive no penalty, and an exactly unchanged
clean pair supplies no coherent gradient. The original absolute, common,
paired-difference, DC and flat losses remain necessary. A stronger projection
can still coexist with false texture or overfitting; there is no noisy-sky or
real-fence recovery claim without actual matched training and image comparisons.

All **25 focused CPU checks** pass. Independent NumPy values and analytic
derivatives agree for heterogeneous pair energies at three floors. Tests cover
descent on a missing weak wave, target detachment, pair symmetry, vanishing
signal, constant/orthogonal blind directions, empty pairs and invalid contracts.
The empty-pair zero stays connected without summing finite values into overflow.
Both paired and unpaired wrappers preserve every old scalar and mask exactly.

The CPU replay reuses all 20 audited native RGB batches from V182 at the completed
raw V180/V181 states. All neural Module calls are forbidden. Its independent
NumPy formula checks the new per-pair values and all **53,477,376 weighted
output-gradient coordinates**: maximum loss difference 1.15e−8, with zero observed
FP32 gradient differences or relative L2 error. All four mixed/flat batches at
both states supply connected zero gradients. CPU RNG stays unchanged, CUDA stays
uninitialized, and no optimizer, new source/noise, parent/DINO or RAW decode runs.
This does not verify a network-parameter gradient or a finite optimizer update.

The first 20-check run passed with a test-only requires-grad scalar-conversion
warning. Its source and log remain preserved. Scalar detachment and import/style
cleanup remove that warning; five added contract/overflow checks bring the total
to 25. The empty-pair implementation also avoids a possible finite-sum overflow;
nonempty projection math is unchanged. Native replay uses the final exact sources.

The actual CUDA probe completes two native four-image updates, mesh then mixed,
from V172's real 141 Adam states at900 plus a zero local-evidence adapter with
no optimizer history. Both nine-term FP32 totals match independently. The new
loss and all6,291,456 output-gradient coordinates match CPU with zero observed
differences; all142 trainable tensors have finite/nonzero gradients at both
updates. Model/Adam/EMA/CPU-CUDA RNG restoration between them is exact, with
zero prefix replay. Counts are two wrapper/frozen/network/projection and ten
samplers; peak allocation is6.292GiB. Independent CPU inspection strictly loads
both raw/EMA/frozen/Adam checkpoints at network901/902 and adapter1/2. These
probe checkpoints never initialize the matched trial.

The original matched continuation is now running from the same V172 initializer
and zero adapter used for V180/V181. It adds900 updates/3,600 images over the same
1,000 cached rows with100 ADC skips, keeping domain weights,LR,EMA and sampler.
All754 worker files are frozen, including98 unchanged neural files. Seven helper
bodies stay exact; the training body changes only its objective import. Actual
row8 restoration resumes at row9. One immutable live-prefix observation verifies
575 completed rows and514 exact nine-term totals, with unchanged input/mask/LR
bindings. This is not the terminal training audit or a quality result.

Separate preparation passes44 audit CPU checks,14 comparison checks and16
publication guards. A positive audit fixture caught a stale prior method-prefix
predicate after43 passes/one failure; source/log are preserved, and the corrected
predicate uses the configured evidence methods before freezing or scientific
audit use. Full marked fixtures retain19methods/15,618rows/32contrasts/1,218cells
and60nativefigures/12triplets/15sheets, using old V181 values/pixels explicitly.
They establish no new quality. The ten-state viewer fixture retains all eight
older checkpoint entries exactly, defaults V181 EMA/V183 EMA, and is rejected
by actual browser/pixel entries. A new480-screenshot fixture is unnecessary for
the unchanged viewer template; actual480crop verification remains required.

The completion controller adopts the original training owner, runs full audits,
one review, reduction and rendering, then stops for all15 actual sheet inspections.
Measured V181 same-format artifacts total619,215,007 external bytes; the new trial
forecasts0.65GiB externally plus a separate0.08GiB admission, with local/external
reserves48.5/111.5GiB. Native arrays, checkpoints and exports use the external SSD.
[Actual CUDA, training launch and helper evidence](results/v183-coherent-pair-CUDA-and-trial-preparation-v1.json).

Remaining work is terminal training/quality audits, both endpoint reviews,
actual native inspection, exports and browser/publication verification. Those retain
the V180/V181 and earlier useful strengths, the complete quiet/absent/ADC controls,
both protected GFX scenes, main sky/building/foliage/coarse fence and both fine
cab ROIs/profiles/JPEGs. Any claimed quality improvement needs at least two
unresized native noisy/restored/exact constructed-GT triplets with identical
source/ROI/noise/display transforms and checkpoint hashes. Independent
ISO100/AHD/JPEG references remain qualitative, not exact GT. Captures, JPEGs and
siblings stay excluded from training; originals and unavailable `/mnt/dataz`
remain unused. Fine crossings and broad colored mottle are still unresolved.
