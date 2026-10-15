# Real RAW pipeline and camera-conditioning failure

Implemented model-independent integer registration, exposure matching, calibrated
auxiliary AHD references and measured-clean-CFA targets. Fixed grids, source/crop
checksums, frozen weights, source archives and scene-level aggregation make the
development evaluations reviewable. All four Bayer phases and odd shifts are
tested. The complete suite passes 100 tests; Ruff check and format pass.

Corrected RawNIND preprocessing after inspecting its pinned publisher source:
preserve signed/out-of-range observations and convert camera-white units to its
global ADC normalization. Its model and weights remain external under their
upstream license. Historical clipped-input reports are retained as historical;
new comparisons must use the corrected, stronger baseline in IEEE FP32.

Four known-sensor development scenes (8 noisy captures, 72 crops) favor RawNIND:
54.0686 measured-sensor dB vs V6 step51000 51.2225. Rendered auxiliary PSNR/SSIM
is 39.6780/0.92881 vs 36.9006/0.86953. V6 step20000→51000 gains little on these
real scenes. Inspected outputs retain grain, color mottling and isolated specks.

Acquired five additional publisher-marked unknown-sensor M100 development scenes,
outside the official test reserve: 20 RAWs, 10 noisy captures, 90 crops, all checks
passed. V6 performs severely worse: 36.4487 sensor dB / 18.9351 rendered dB versus
RawNIND 53.5622 / 38.1448. A ten-center-crop counterfactual replacing only the
conditioning matrix with identity improves rendered PSNR 18.0852→32.7799 dB.
This points to conditioning extrapolation: training matrices were close to identity
and WB red never fell below 1.3, whereas these real scenes have red WB near 0.9 and
substantial primary mixing. Changing metadata is a diagnostic, not a production fix.

The original 100000-step V6 job continues as a control (~67000 steps at this
review). Next: broaden physical camera augmentation and evaluate real denoising.
All 16 official paired test scenes and 2255 Commons test sources remain unused.
The requested quality goal is not achieved. Results are summarized in
`docs/results/paired-real-development-v6-51k.json`; full reports remain in
`/mnt/external/demosaic/evaluation/paired-{raw,unseen}-development-v6-51k`.
