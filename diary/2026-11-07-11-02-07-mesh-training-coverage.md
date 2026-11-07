# Mesh training geometry and contrast coverage

Recorded: 2026-11-07T11:02:07-08:00 (America/Los_Angeles).

Audited the original V160 cache while the unchanged V167 bounded-support trial
was training. The [machine receipt](../docs/results/mesh-training-coverage-20261107-v1.json)
preserves the complete executed source, source/cache/reference hashes, all 682
pair rows and separate noisy/ADC-only aggregates. Both clean sensor fingerprints
were independently reconstructed from retained target RGB and Bayer colors for
every one of 341 batches. The analytic geometry Jacobians agree with coordinate
finite differences in all 72 checks (maximum difference 4.24e-11).

Of 614 noisy mesh pairs, 202/1,228 center carrier periods fall in the qualitative
reference's dominant 7.12–9.40 pixel interval, with both families covered in
13 pairs. Nominal 6–32 pixel periods therefore include the desired range but
give it limited joint coverage. Projective transforms occur in 126/614 noisy
pairs. Five-point Jacobian estimates account for these transforms; they are
not actual post-mask/interpolation/reduction spectral peaks.

Actual clean sensor pair-difference RMS has median 2.48048 DN16 and 10th/90th
percentiles 0.374424/15.6579. 264 pairs have RMS below 2 DN16, including 47 with
even the peak below 2 DN16. The median full-context input signal/noise RMS
ratio is 0.00931554, an energy proxy rather than matched-filter detectability.
The 68 ADC-only pairs remain separate. The real reference periods come from
independent ISO100 AHD/JPEG renderings, not exact GT or training pixels.

A plausible later data test would deliberately cover both fine carrier families
and a signal/contrast ladder while retaining matched empty scenes. Reducing
contrast alone is not supported by this audit: many existing examples are
already extremely weak. This does not establish a cause of the model's closed
support or a restoration gain. No new neural inference, sensor sampler,
training source construction, original media or /mnt/dataz access occurred.
V167 and its frozen publication sources are unchanged; its quality is pending.

