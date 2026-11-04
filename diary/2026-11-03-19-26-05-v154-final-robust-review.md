# V154 final robust spectral review

Recorded: 2026-11-03T19:26:05-08:00 (America/Los_Angeles).

Review completed: 2026-11-03T19:47:42-08:00 (America/Los_Angeles).

V154 is complete: three fresh matched 1,000-update relative heads compare exact
V153 delivered-RGB MSE against stable Charbonnier .01/.003. All six raw/EMA
endpoints were fixed in advance. The completed trial gives small useful
standalone-flat gains but does not solve weak detail beside clean quiet regions.

Native512 noisy-flat RMS falls 0.45–0.50% versus V143, and present-mesh actual
blank RMS falls 0.21–0.27%, both better than matched MSE. Broad colored mottle
remains. Mesh response is only 2.29–2.41% of constructed GT, below MSE, and
natural-band response falls further. Exact quiet masks beside steps/bars/patterns
have 1.51–2.27% higher RMS than V143, worse than MSE. Strong-edge whole-scene
averages conceal this quiet-neighbor cost. No convincing new real cab crossings
or organic texture appear.

All 288 constant ADC-only predictions are bit-exact parent. All 32 robust
ADC-photo arrays are also exactly parent: this avoids the MSE regression but
loses V150's roughly3.06% ADC gain. Sloped full/coarse error worsens. Support
means open while proposal energy falls, without useful present/absent
selectivity. The loss changes relative weak pressure and overall gradient
strength together; it is not an equal-gradient-norm experiment.

Training and every postprocess stage succeeded without restart. All 12 recorded
owners are terminal. All 39 Adam states are finite at step1000; no clipping in
production. The MSE control exactly reproduces V153 RGB trace/raw/EMA/Adam and
all 1,644 quality arrays. Independent audit checks54,246 scalars across6,330 rows,
maximum discrepancy5.1159e-13 and656 Decimal reductions. Real ISO100/AHD/JPEG
references remain qualitative and all42 real rows unscored.

Actually viewed84 original native figures in21 unscaled sheets and12 additional
flat triplets in3 sheets, after the image-tool outputs arrived. The new flat
triplets directly document the narrow gain and persistent mottle, using two
fixed ISO priors for each endpoint; they add no observations or inference.
All96 PNGs/48 triplets retain160px native cells and45,235,200 checked RGB channels.
Source/ROI, checkpoint hashes, conditioning, exact target anchors, contrast and
exposure are in the manifest. Both DSCF3879/3880 and DSCF3842/3835 scenes retain
all windows/priors and both JPEGs, with sky/building/foliage/fence controls.

Actual head evaluations:56 compatibility +30 discarded smoke +3,000 production
+4,932 review =8,018, excluding objective unit tests. No new parent/DINO calls,
noise draws, original lookups or RAW decodes. All86 neural sources unchanged.
Local/external endpoints remain split two/four with96/208GiB free-space reserves;
all inputs and old evidence remain in place. Protected originals remain
read-only and excluded with their siblings/JPEGs; /mnt/dataz was unused.

Published23 byte-exact final receipts plus all96 figures, preserving all14
preparation copies,19 source texts, checkpoint250 audit and historical294-row
live snapshot. The final helpers and report builder are retained in publication
provenance. README now shows two native robust flat triplets beside prior mesh
strengths; current-model, research, experiment and documentation indices report
the gain and cost directly. Historical machine UTC timestamps stay byte-exact.

Next examine a cleaner parent and spatially local supervision. The late
band-limited head cannot directly remove the parent's affine/DC or out-of-band
coarse mottle. V120 has earlier measured coarse-flat advantages over V143; a
matched fresh-head study would test whether that survives these inputs. This is
a next hypothesis, not a completed improvement. Keep V153 stronger mesh
response, V151/V152 quieter controls, V150 ADC gains and V154 standalone-flat
gains as distinct comparators. The broad fine-dark-detail/clean-sky goal remains
active; no default inference change.

[Full report](../docs/robust-spectral-objective.md) ·
[Final evidence](../docs/results/v154-robust-spectral-final-v1.json) ·
[Publication verification](../docs/results/v154-robust-spectral-publication-verification-v1.json).
