# Closed carrier coverage and weak-response limits

Recorded: 2026-11-16T07:01:01-08:00 (America/Los_Angeles).


The previous goal turn made progress by preparing the matched full-model review;
this turn verified the exact live training/review processes and joined the
complementary branch's closed input-only proposals with its actual conditional
weak-response measurements. No trained weight changed.

At the 400 prior/far edge, 32/64 views from seven sources acquire weak-fundamental
proximity within three native DFT bins only through the additional bank. Their
weak response rises 4.318%→6.252% (+1.934 points). Seventeen inherited-coverage
views from four sources rise 17.694%→18.800%; 15 remaining views from five sources
rise 5.467%→5.606%. Weighted group differences exactly recover the overall
 +1.2935-point gain; newly covered views contribute 0.9669 points, about 75%.
These groups overlap sources and differ in difficulty; this arithmetic is not
a causal estimate of allocating a carrier. At 1600/far the 12 newly covered views
improve 3.007%→4.450%, with slightly higher quiet error.

Using the pre-existing stricter one-native-bin threshold, 48/64 clearest/far
views cover all eight sources but still average only 10.704% weak response.
Nearby global frequency alone therefore does not ensure good output. This does
not establish the measured basis's reconstruction capacity: local phase/color
fits, finite support and learned modulation/shrinkage remain unresolved. A useful
next diagnostic holds those carriers fixed and compares known-target fitting
of the same measured basis with the learned correction, explicitly as an oracle
analysis rather than an inference confidence score.

Verified all 384 closed batches on CUDA with the exact trained-evaluation package:
768 selector calls, 36,864 integer coordinates, 18,432 validity values and 603,979,776
measurement-field channels are exact. Neural construction/forward callbacks
are forbidden; no model/readout/parent/DINO calls, noise/source draws, updates or
training signals occur. RNG remains unchanged. Peak allocated CUDA memory is
99,623,936 bytes under a 2 GiB cap; the concurrent training worker remains live.
This posthoc backend verification does not make the original proposals an
independent discovery or confidence procedure.

A CPU-only analysis independently recomputes 6,912 geometry distances (maximum
error 2.84e-14 native bins), checks 9,984 exact zero-gain metrics against full
V200EMA, and verifies source/placement/CFA/repeat/array identities and complete
bank concatenation. Both endpoints, all three profiles and both 1/3-bin thresholds
remain available. 17 focused tests and Ruff pass. Hardened invalid-geometry
rejection preserves every actual analysis row/group/audit exactly; the original
analysis and its exact source bytes remain archived. The final scientific figure
was inspected. The earlier draft figure remains in the cache unchanged.

Two zero-work prefixes are preserved. The first source gate incorrectly included
the older unused competing comparator; both selector files actually replayed
are byte-exact to their closed bindings and actual evaluation package. The
second launcher resolved the venv Python symlink, lost installed Torch, and
stopped before Torch import/worker admission. Corrected launch uses the venv
interpreter directly. Successful owner 176041/create1794840393.59 completed the
single declared 768-selector check. No existing model evaluation or training was
restarted. These mistakes changed no scientific inputs or choices.

[Report, two unchanged native exact-GT triplets and diagnostic plot](../docs/complementary-coverage-quality.md)
retain the existing trained checkpoint/source/noise/ROI/display provenance.
[Exact archives](../docs/results/complementary-coverage-quality-v1/publication.json)
preserve both failed prefixes, original analysis/source and all verification
receipts. The same two protected GFX families and existing flat/color failures
remain documented in the full model review. V120 remains recommended. The
full-model RAW-attention trial and its matched endpoint reviewer remain active.
