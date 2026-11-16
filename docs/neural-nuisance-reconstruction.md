# Whole-context neural nuisance for withheld RAW detail

The matched correction pilot is running. It tests whether a richer background
can prevent scene structure from masquerading as weak periodic detail. The
earlier [two-context diagnostic](withheld-neural-background.md) improved
prediction of withheld noisy sensor samples, but did not test delivered
restoration quality. No quality improvement is claimed for this pilot yet.

The [implementation](../src/demosaic/neural_nuisance.py) uses frozen V120
backgrounds computed from half the sensor samples, with the other half filled
using only same-phase discovery measurements. One whole-context CFA partition
is shared by the neural input and every overlapping analytic tile. Reverse the
partition for a second independent proposal. The actual neural arguments must
remain identical when all withheld observations are replaced by NaNs.

Each tile fits one own-color neural coordinate alongside the existing
edge/affine nuisance. Frequencies are selected again from that residual, then
the two H1 directions and nuisance are fitted jointly per color. Sensor-white
clipping applies only to the neural coordinate; negative read values remain.
The analytic control shares the same discovery partition, A-only edge geometry,
analytic noise proxy, cardinality matching, validation windows and fixed
thresholds0/2/4. Neural context size is part of the intervention; this does not
isolate the effect of adding one scalar basis function.

The primary comparison uses **conditional analytic H1 versus conditional neural
nuisance, local threshold2**. Each delivers the unique full-minus-null
prediction, projected against the full-input parent only after scoring. A
neural nuisance can correlate strongly with a sinusoid, making its raw fitted
coefficient ambiguous. The conditional prediction is the component tested by
held-out validation. A separate analytic raw-sinusoid arm measures the delivery
change. Residual wave Gram eigenvalues are diagnostic, not calibrated support
probabilities or an extra tuned gate. The final parent uses the full input;
withholding does not make the final restoration an independent estimator.

The frozen48-case development cohort contains36 finite-wire roles from two
sources, near/far placement, RGGB/repeat0 and the original400/1600/6400 priors;
the other12 contexts retain the material and both standing GFX families,
profiles, ROIs and JPEGs. These sources have been adaptively reused. All88
whole-context background fields and all48 corrections must close before new
GT/reference scoring. Four explicit shot=read=0 controls bypass the neural
background and return the parent exactly. No source/RAW decode, fresh sensor
observation, optimizer update or training admission is involved.

The procedural full-input parent is V143, checkpoint SHA256
`96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4`.
The photographic parent and all withheld background teachers are V120,
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
The official DINO backbone hash is
`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.
The producer checks all91 restoration tensors and the backbone before/after
inference, and counts fresh model/encoder calls. A closed background cache can
be reused only with matching physical-input, mask, argument and checkpoint
bindings.

The review will report weak/strong response together with quiet, increment and
absolute role errors, fixed threshold curves and bad real crops. Both protected
real-photo families and their siblings remain outside training; their ISO100
and independently demosaiced references are qualitative, never exact GT or
pixelwise scoring targets. Native160 comparison crops and at least two exact
synthetic noisy/restored/GT triplets are required before reporting a gain.

All88 background fields have now closed in156.70s including load/verification,
with exactly88 root and88 encoder forwards and all91 restoration/backbone
tensors unchanged. This concurrent run is not a speed benchmark. An independent
CPU audit checks70,778,880 finite FP32 output values, all physical/argument
fingerprints and actual withheld-NaN invariance. Its independently implemented
finite Gaussian stencil matches every masked neural input exactly. It loads
no target/reference/parent RGB and performs no neural inference. Correction
quality remains pending.
