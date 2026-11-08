# Bounded coherent pair-response supervision

**V183 has a CPU-verified loss implementation; trained quality is unmeasured.**
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

Next required work is actual CUDA/network-gradient and restoration checks,
followed by the matched continuation and both endpoint reviews. Those must retain
the V180/V181 and earlier useful strengths, the complete quiet/absent/ADC controls,
both protected GFX scenes, main sky/building/foliage/coarse fence and both fine
cab ROIs/profiles/JPEGs. Any claimed quality improvement needs at least two
unresized native noisy/restored/exact constructed-GT triplets with identical
source/ROI/noise/display transforms and checkpoint hashes. Independent
ISO100/AHD/JPEG references remain qualitative, not exact GT. Captures, JPEGs and
siblings stay excluded from training; originals and unavailable `/mnt/dataz`
remain unused. Fine crossings and broad colored mottle are still unresolved.
