The fresh matching residual improves standalone-flat error while retaining the
V169 detail response. EMA full-flat RMS falls **1.21% at ISO6400 and 1.52% at
ISO12800**, and coarse32 RMS falls **1.73% at both priors**, versus V169 EMA.
All 48 native noisy-flat inputs improve in both measures. Raw also improves all
48 coarse inputs, with 42/48 full-RMS improvements. This is a useful flat-field
option above the existing DINO restoration, not a general upgrade.

Mesh response rises **1.04–1.26%**, reaching **3.876–3.885% of exact constructed
amplitude**. Present-mesh RMS falls 0.47–0.52% and wholly absent RMS falls
0.98–1.09%. The native gain is subtle: seed2302 remains almost flat and seed2309
keeps mainly one diagonal family. The real green cab fence retains incomplete
strands under both priors; the weak crossing family is still missing. Main sky
looks smooth at ordinary exposure, while building, foliage and coarse fence are
close to V169. Neither a clear new lattice nor flat-region safety is established.

The quiet-color cost is substantial. EMA quiet RMS rises **30.73%/25.78%** at
ISO6400/12800, to **5.289473/7.979617 DN16**; DC color error rises **91.04%/93.22%**.
Quiet spatial RMS falls only 0.29–0.61%. Raw quiet RMS rises 42.80–51.10% and DC
error 140.68–142.11%. Actual amplified quiet crops show stronger purple/blue casts
and remaining blotches, although ordinary-display step/bar edges look clean.
Whole-context or standalone-flat gains do not excuse this nearby-region failure.

Natural photographic band-error means improve slightly in all four cohorts,
while full-RMS means worsen in three of four; the retained-faint improvement is
only about0.002%. Bird, butterfly and plant microtexture remains heavily smoothed.
All 144 ADC-only results retain V169 exactly, including smooth planes and
bark/fur texture; the new branch adds none of V170's periodic ADC artifact.
This is an exact bypass property, not a learned ADC improvement or a guarantee
for noisy flats.

All 60 fixed native figures were actually viewed at original detail, including
both protected GFX scenes, both cab priors/windows and both JPEGs. Separate
ISO100/AHD/JPEG views remain qualitative references, not exact GT. Keep V171's
full/coarse-flat option beside V169 quiet color, V161/V164 stronger learned
response, V165 grain and earlier useful choices. V120 remains the general
recommendation. Greater matching capacity at this schedule does not by itself
solve the fine-crossing and no-fabricated-structure objective.

The training worker completed 900 updates and 100 ADC skips with an actual
step-8 restoration and no prefix replay. Quality completed both fixed endpoints
on all 822 cases; all 1,644 frozen V169 outputs replay exactly. The first review
initialization missed a metric helper and stopped before any neural call. Its
claim/log/source are preserved, the verified helper was added through a separate
receipt, and the original inference source and plan stayed unchanged. The
corrected worker repeated no completed scientific inference. The future
preparer now includes that dependency.

[Runtime dependency evidence](results/v171-runtime-dependency-preparation-v1.json)
· [Future preparer correction](results/v171-preparer-dependency-fix-v1.json)
· [Training-audit counter clarification](results/v171-training-audit-scope-clarification-v1.json).
