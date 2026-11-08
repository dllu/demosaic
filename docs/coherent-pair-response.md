# Bounded coherent pair-response supervision

**V183 has completed training, both endpoint reviews and actual native inspection.**
The [completed comparison](coherent-pair-evidence-comparison.md) recovers EMA
mesh response **6.95% versus V181 to4.439% of exact constructed GT amplitude**,
with quiet spatial RMS **0.39–0.67% higher** at ISO6400/12800. All32 quiet
inputs worsen spatially. Against V180, response is2.41% lower and spatial
quiet RMS0.09–0.49% lower. Natural fine-band response rises slightly versus
V181; broad mottle and missing real fence crossings persist. Retain this
intermediate recipe beside V180's stronger response and V181's quieter output.

The [V182 gradient study](flat-spatial-gradient-conflict.md) finds that added
spatial pressure can oppose weak-detail response through shared parameters.
This follow-up adds direct coherent response supervision while retaining all
eight V181 terms, their FP32 total order and the existing clean mask. The
architecture and all 98 neural source files stay unchanged. Earlier
[V180/V181 quality](flat-spatial-evidence-comparison.md) remains available
alongside both V183 endpoints and earlier useful strengths.

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

The original matched continuation finishes from the same V172 initializer
and zero adapter used for V180/V181. It adds900 updates/3,600 images over the same
1,000 cached rows with100 ADC skips, keeping domain weights,LR,EMA and sampler.
All754 worker files remain frozen, including98 unchanged neural files. Seven helper
bodies stay exact; the training body changes only its objective import. Genuine
row8 restoration resumes at row9 with zero prefix replay. The immutable575-row/
514-total live observation remains historical evidence. The terminal independent
audit now passes all1,000 rows,900 exact nine-term FP32 totals, masks, LR and
five strict raw/EMA/Adam/frozen/RNG checkpoints. Network clocks finish1,800 and
adapter900. Peak training CUDA allocation is6,787,514,368bytes, about6.32GiB.

Separate preparation passes44 audit CPU checks,14 comparison checks and16
publication guards. A positive audit fixture caught a stale prior method-prefix
predicate after43 passes/one failure; source/log are preserved, and the corrected
predicate uses the configured evidence methods before freezing or scientific
audit use. Full marked fixtures retain19methods/15,618rows/32contrasts/1,218cells
and60nativefigures/12triplets/15sheets, using old V181 values/pixels explicitly.
They establish no new quality. The ten-state viewer fixture retains all eight
older checkpoint entries exactly, defaults V181 EMA/V183 EMA, and is rejected
by actual browser/pixel entries. These marked fixture pixels are not V183
quality. The actual ten-state viewer is built separately from completed results;
[browser pixel verification](results/v183-coherent-pair-native-viewer-verification-v1.json)
checks480 actual crops and36,864,000RGB channels, with both raw/EMA metadata,
click/F flipping, navigation and no JS errors.

The completion controller adopts the original training owner and completes full
audits, one review, reduction and rendering. All15 actual original-detail sheets
are now inspected, covering60 native figures and12 unresized triplets.
Measured V181 same-format artifacts total619,215,007 external bytes; the new trial
forecasts0.65GiB externally plus a separate0.08GiB admission, with local/external
reserves48.5/111.5GiB. Native arrays, checkpoints and exports use the external SSD.
[Actual CUDA, training launch and helper evidence](results/v183-coherent-pair-CUDA-and-trial-preparation-v1.json).

Actual review completes1,644 wrapper/frozen calls,1,500 network/projection,
7,500samplers,1,644 exact frozen replays and144ADC identities. Independent quality
audit verifies6,576 input bindings,72RGB+72residual arrays,53,772,288 addition
channels,582 native scalars,278Decimal means and750 exact raw/EMA input-evidence
pairs. This does not calibrate the spectrum or confidence. Reduction retains
19methods/15,618rows/32contrasts/1,218cells with2,591Decimal means and12,870paired
checks. The development inputs are reused and atomic sampler backward remains
warn-only nondeterministic; no blind or seed-uncertainty estimate follows.

Two strict CPU exports bind checkpoint SHA256
`4d6d47cc14ef3effb9569d867c5aed59a1e09b315de6bbb82e61281e928b3962`:
raw `0cb648cad95a6040181e149a76f541b206c539a33a25e19efbce931de37a4a21`,
EMA `b713608498158b24b09da72c8079d6eae58bc2458f7d4ac63d493b7b679f63b3`.
[Actual evidence](results/v183-coherent-pair-evidence-final-v1.json) ·
[Publication verification](results/v183-coherent-pair-evidence-publication-verification-v1.json).

The report retains V180/V181 and earlier useful strengths, complete quiet/absent/
ADC controls, both protected GFX scenes, main sky/building/foliage/coarse fence
and both fine cab ROIs/profiles/JPEGs. It includes12 unresized native noisy/
restored/exact constructed-GT triplets with identical source/ROI/noise/display
transforms and checkpoint metadata. Independent ISO100/AHD/JPEG references
remain qualitative, not exact GT. Captures, JPEGs and siblings stay excluded
from training; originals and unavailable `/mnt/dataz` remain unused. Fine
crossings and broad colored mottle are still unresolved.
