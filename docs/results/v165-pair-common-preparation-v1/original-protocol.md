# Absolute supervision of shared pair error: V165

V165 tests whether direct supervision of errors shared by a training pair can
retain V164's stronger weak-detail response with fewer quiet-region artifacts.
**Training and quality review are in progress; quality is unmeasured.**
[V164 gains and costs](pair-unit-floor.md) remain the latest completed comparison.

For RGB errors `e_a = output_a - target_a` and `e_b = output_b - target_b`, the
existing paired-response term sees `e_a - e_b`. Equal errors cancel. The new
term sees `(e_a + e_b) / 2`, retaining each member's actual, distinct target.
It uses stable pseudo-Huber `z² / (sqrt(1 + z²) + 1)` with a fixed 16 DN16 unit.
The trial compares added weight **0 versus 1**, including the inherited domain
weight. Both arms retain the difference loss at weight 1, floor 2 DN16 and
Charbonnier epsilon .003, plus the .25 flat-target anchor and all other losses.

The common and opposite pair subspaces are orthogonal at the output. That
property does not carry over to shared network parameters or guarantee a
favorable training result. The common term also sees shared sensor noise;
its units are training weights, not an estimated covariance or confidence.
It cannot see opposite errors, so the difference and ordinary reconstruction
losses remain necessary. Targets and pair metadata never enter inference.

## Evidence for the test

A fixed diagnostic runs the actual V164 raw and EMA heads on the six paired
batches in the original ten-batch training prefix. It uses **12 root calls /
48 head images**, without parent/DINO calls, new sources or new noise. These
are training examples, not held-out quality measurements. Predictions remain
external and the original diagnostic owner is terminal.

The average common fraction of pair MSE is 87.7–87.8% for the two mesh batches,
56.7–56.8% for the two photo batches and 80.3–80.7% for the two weak batches.
Individual fractions span 55.0–99.0%. Common error includes shared noise,
spatial bias and missing detail; this result does not identify their separate
causes. Existing absolute losses already supervise common error. The proposed
addition tests stronger direct pressure rather than introducing its first
supervision.

The exact squared-error identity is
`mean_pair(e²) = common² + (e_a - e_b)² / 4`. The pseudo-Huber penalties do not
have this additive identity. Independent FP64 replay checks 48 actual diagnostic
scalars. The CUDA loss and complete output gradients match NumPy, with maximum
adjoint discrepancy 1.41e-9. Equal pair-member gradients verify that this term
acts in the intended output subspace.
[Diagnostic, immutable sources and actual outputs](results/v165-pair-common-motivation-v1.json).

All **221 CPU checks** pass, including 22 new independent value/full-adjoint,
common/opposite-error, target-preservation, permutation, tiny-error, zero-ADC
and invalid-input checks. All 89 neural modules remain byte-identical.

## Fixed matched trial

Two fresh identical 124,909-parameter / 47-tensor phase heads reuse all 1,000
V160 B4 batches and frozen V143 parents. Initialization, source order, RAW,
targets, pair units, loss components, optimizer, LR, clipping and EMA clocks
match V164. Only the added common-error loss differs. The control must reproduce
all 1,000 V164 candidate trace rows and final raw/EMA/Adam states, then replay
all 1,644 actual archived outputs before adopting their storage.

The plan includes genuine restored 8+2 smoke, four strict final CPU loads and
94 finite final Adam states. A 28-context / 56-call parity check covers all
CFAs, native 256/384/512/768 contexts and both real scenes. Twenty additional
leaf-output CUDA backwards check ten inherited flat-anchor, six pair-unit and
four new common-error cases; these are not neural forwards. The motivation
probe's twelve additional leaf backwards are recorded separately.

Both final raw/EMA endpoints of both heads receive the same 822-case review:
3,288 actual review calls, 1,644 new external predictions, independent metrics
and all paired costs. Main trial work totals 5,364 root calls / 11,424 head
images, plus the twelve motivation calls / 48 images. The new study reserves
56 GiB locally and 136 GiB externally, plus a .5 GiB projected margin and a
.25 GiB remaining local artifact bound. CUDA is capped at 12 GiB; launch/runtime
RAM floors are 52/32 GiB. Older evidence remains intact.

The fixed native comparison plan retains 72 images / 24 noisy-restored-GT
triplets, eight historical comparator columns and 61,824,000 independently
checked RGB channels. Native 160×160 pixels are never resized. Source/ROI,
checkpoint hashes, conditioning and common display exposure will be retained.
Actual viewing follows rendering; no prospective viewing claim is made.

Both protected GFX scenes remain mandatory: DSCF3879/3880 sky, building,
foliage and coarse fence, and DSCF3842/3835 fine cab mesh under both priors,
both windows and both camera JPEGs. ISO100 f/5.6 captures differ in aperture,
shutter and motion: qualitative references, not exact GT. These captures,
JPEGs, siblings and all 18 held-out Commons IDs remain outside training.
No originals or `/mnt/dataz` are accessed.
