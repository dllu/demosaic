# Measure local weak-detail response from saved material outputs

Recorded: 2026-10-24T18:55:31-07:00 (America/Los_Angeles).

Added a GT-only local fine-band diagnostic to test whether the high whole-patch
gain in the V114 pilot hides weak-region attenuation. The frozen analysis
reuses all12 material inputs and five methods' original FP32 predictions. It
partitions each240px interior into225 disjoint16px blocks, using orthonormal
DCT-II and radial1/8–1/3-cycle frequencies. Relative GT band RMS/mean bins,
mean/range eligibility and minimum band RMS were fixed before output analysis.
All2700 block observations are retained:900 unique source blocks repeated
across three conditions,772 eligible per condition.

The<2% group contains112 blocks from only two materials:84 feather and28 fur.
Bark and canopy contribute none. V114 eight-view source-balanced projected
gain is.96354/.90307/.31813 at ADC/ISO100/ISO12800; the strongest high-noise
group is.94254. Whole-patch gain therefore does not characterize these weak
subregions. High-noise weak-group gain falls from V114 single.32161 to.31813
under averaging, while pooled orthogonal RMS falls.00361068→.00349961 and
error RMS.00717149→.00715576. V112 eight-view weak gain is.32798; this is not
evidence that the latest weights or averaging solve faint structure.

The explicit cosine transforms agree with independent even-extension FFT
coefficients within1.41e-14. A closed-form fixture recovers gain.75 and
orthogonal RMS.0001, with spatial Parseval checked separately. All target
fingerprints match across conditions. Torch was not imported; there were zero
neural/encoder calls, optimizer updates, new noise observations or RAW decodes.
No source original or training data was modified. The first execution passed;
the original frozen source, plan, result, block details and logs are retained.

Actually viewed two unchanged native160 feather/fur triplets and the new
three-panel scientific figure. The triplets repeat earlier board pixels and
illustrate mixed-contrast contexts, not isolated16px weak blocks. Fine feathers
and hairs are visibly smoothed. Published [the analysis](../docs/local-material-detail.md),
[bound results](../docs/results/local-material-detail-v1.json), figures and
[original crop receipts](../docs/images/local-material-detail-v1/manifest.json),
and updated current detail/model/research guides. No model choice, primary
PSNR-history point, inference default or frozen V116 recipe/queue changed.

This is exploratory linear-luminance evidence, with variable source coverage,
possible coarse-boundary leakage and finite noise/GT correlation. It supplies
no new deployable correction, statistical uncertainty or real-camera claim.
Held-out blocks remain diagnostic, not training examples. At18:55 PDT the
original V116 worker was live at7475/20000 with finite logged metrics; all
downstream owners remained live and waiting for their exact dependencies.

