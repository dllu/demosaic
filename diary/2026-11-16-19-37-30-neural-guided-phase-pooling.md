# Guide phase pooling with withheld neural signal

Recorded: 2026-11-16T19:37:30-08:00 (America/Los_Angeles).

# Projection diagnostic and intervention

The previous completed phase trial yields a real capacity gain but higher
quiet/increment error and building bands. Checked oblique background projection
before changing it:168 actual color/direction operators, both400/far sources,
building and nominal cab. Largest noise-weighted residual norm1.01549; finite
maxima<1.00014, actual parent-residual norms almost unchanged under a stable
orthogonal-null diagnostic. This rejects large global residual amplification
as the main explanation on these inputs; it does not exclude local mixing.
No GT/reference arrays or neural replay, original geometry checked exactly.

Implemented own-color A-only neural range guidance for phase pooling. Physical
shot/read square-root coordinate, fixed two-noise-unit bins and[1,2,1]/4 range
smoothing, same129/32/32-bin phase geometry and global background/competitor.
Positive normalized measurement weights; phase-minus-local difference signed.
Each color keeps its own measurements/amplitude, no parent guide, no green-to-
red/blue inference. Both phase nuisance arms share the same guide; H1 retains
its original scores. Direct query histograms avoid a huge native4D volume.

38 focused tests and78 existing regression tests pass. Tests independently
enumerate actual phase/range measurement weights for all four CFAs, reproduce
the old kernel for constant guidance, verify actual NaN withholding/linearity/
parent projection and nonzero H1 parity, and isolate a two-object profile
without tying color amplitudes. These are operator properties, not real-photo
quality or calibrated confidence.

Launched48-case pilot once: producer874907/create1794886618.88,
predictor874954/create1794886626.84, reviewer874908/create1794886618.9.
Plan3735fe54cdb0136f9528b6c7859a2cc970c675051f50323cab6100aad8e89dcb.
Adopt88 exact fields, zero NN/DINO calls. CPU14/15, two threads; all outputs
close before GT/reference scoring. Primary localt2, fixed0/2/4 controls.
Both protected GFX families, all ROIs/profiles/JPEGs retained outside training;
references qualitative, never exact GT. Originals remain read-only.

The original full1164-case sinusoidal producer/reviewer are untouched, without
partial full-quality analysis or restart. [Protocol/report](../docs/neural-guided-phase-pooling.md).

## Completed quality review

All48 corrections/all seven producer stages, scoring/audits and follow-up
review succeeded normally. Zero fresh NN/DINO calls. All288 raw-H1 control
arrays equal the prior unguided outputs exactly.116 tests pass; direct
weights, constant-guide parity, cross-object isolation, withholding, identical
parent map and actual nonzero controls are covered. Output audit3819 fields/
228 finite/114 material rows/14,131,200 channels, max2.89e-15. All38 published
figures actually viewed in11 exact unresized sheets;178 receipt archives and
166 executed source files retained.

Analytic nuisance with NN-guided pooling is a useful measured phase point:
400/far weak28.702%, strong75.334%, quiet4.03027 DN16, increment11.67713,
full21.38337. Versus unguided analytic, quiet/increment RMS lower0.424%/0.409%
with retained responses. Versus parent quiet+0.541%, increment−0.946%.
Both sources improve increment error versus parent:8.82672→8.73517 and
14.75054→14.61909. Source1 loses some unguided gain; source0 now improves.
This is not broad camera evidence or proof of complete weak fidelity.

Primary neural-nuisance arm fails the error goal: response27.347% nearly
unchanged, quiet+1.744% and increment+3.006% versus parent. Both sources worsen
increment error, to9.14959/15.13646. Higher-noise errors remain; complete
curves/controls/counterexamples stay published. Both phase arms need A-only
NN guide fields; analytic names the nuisance basis rather than NN-free use.

Actual native viewing confirms severe analytic building bands largely removed:
maximum531.58→130.59 DN16,114.31 at the historical[76,260,160,160] ROI.
Neural maximum75.18→55.20. These are changes from parent, not real-reference
errors. Quiet sinusoidalNN15.55 remains smaller. Fine cab crossings remain
missing on both profiles/ROIs; scene-wide maxima now move to bright foliage
outside the fine fence. Sky unchanged, foliage/bark/fur soft. Real references
remain independent qualitative comparisons, never exact GT.

CPU384.33s versus629.08s unguided, two threads; direct query histograms also
change, so this is not a range-guidance-only speed effect or100MP result.
Document the analytic point as an available reconstruction alternative, with
all primary neural-nuisance losses and real limits. README, current model,
research and literature/index now retain those strengths and costs.

## Full guided follow-up

Launched1164-case/all-source/CFA/repeat/noise follow-up once after the completed
pilot review. Primary scientific method is analytic nuisance plus NN-guided
phase`conditional-local-t2` against the completed256 NN baseline. Renderer
primary remains`local-t2` so inherited NN labels remain correct. All six
controls, including the neural-nuisance pilot regression, stay present.
All2320 cached fields adopted;48 exact pilot cases/288t2 outputs eligible by
complete source/configuration/actual-input identity. No NN/DINO replay,
sensor/noise/RAW observation, training admission or learned-weight update.
All1164 outputs close before new full GT/reference analysis. Exact8-source
bootstrap remains descriptive for reused development geometries.

Producer876753/create1794887719.09; reviewer876756/create1794887719.25.
Plan9e30430e1b1f60d6965f8619c9673da219625639f8b1e6a05805007b315913b5;
review a8a528a801f0fda55bc61de3d94c252103c8a2b37b3c94069755eb07f66b67ac.
CPU14/15 producer,18/19 reviewer; original sinusoidal producer stays on16/17.
Exact-owner waiting, no restart.336 frozen source files and12 static launch
receipts are [archived](../docs/results/guided-phase129-full-setup-v1/publication.json).
The [full protocol](../docs/neural-guided-phase-full-panel.md) keeps both
protected scene families/profiles/ROIs/JPEGs qualitative and outside training.

The original sinusoidal full run has closed all1164 corrections and is in
scoring/independent review. Its separate exact-owner publication queue is
prepared; no partial full-quality conclusions have been published.
