V187 pools green-phase and neighboring-frequency measurements at V185's same 508-parameter readout and matched training budget. **Mean constructed mesh response rises 5.23% raw / 3.64% EMA over V185, reaching 5.2273% / 5.3591% of exact GT amplitude.** Both endpoints improve 168/256 present inputs and lose response on 88. Quiet spatial RMS falls 0.03–0.27% raw / 0.48–0.52% EMA. Retain this as the current experimental wave architecture, alongside V185's slightly better absent/flat controls and earlier quieter strengths. V120 Small remains the general recommendation.

## Matched strengths and costs

| Metric versus same-state V185 | V187 raw | V187 EMA |
| --- | ---: | ---: |
| Present signed template response | +5.2283%; 168/256 increase | +3.6395%; 168/256 increase |
| Present full RMS | −0.2703%; only 92/256 improve | −0.1902%; only 90/256 improve |
| Present blank RMS | +0.0448%; 253/256 worsen | +0.0388%; 252/256 worsen |
| Absent full RMS | +0.0348%; all 256 worsen | +0.0341%; all 256 worsen |
| Absent spatial RMS | +0.0371% | +0.0364% |
| ISO6400 quiet total / spatial RMS | −0.2664% / −0.2665% | −0.4457% / −0.5172% |
| ISO12800 quiet total / spatial RMS | +0.00093% / −0.0327% | −0.3431% / −0.4776% |
| Fresh512 full-flat RMS, ISO6400 / ISO12800 | +0.0201% / +0.0215% | +0.0197% / +0.0213% |
| Fresh512 spatial-flat RMS, ISO6400 / ISO12800 | +0.0211% / +0.0225% | +0.0207% / +0.0224% |

Quiet spatial RMS is 3.46624 / 5.61233 DN16 raw and 3.47664 / 5.62165 DN16 EMA for ISO6400/12800. Raw improves 20/32 quiet spatial cases and 18/32 total cases; EMA improves 27/32 spatial and 28/32 total. The quiet DC mean changes −0.0919% / +0.1410% raw and −0.0979% / +0.1648% EMA, so a lower aggregate RMS does not imply uniform color improvement. All 48 fresh noisy standalone flats worsen in both endpoints. Coarse32 changes are mixed and smaller than 0.001% in their fresh-flat means.

Absent signed response is 6.34776e−6 raw and 7.89760e−7 EMA; there is no relative percentage for these near-zero signed values. Lower mean present full RMS also masks many regressions. These repeatedly reused, correlated development cases are not independent scene replications or a blind safety test.

Natural fine-band response rises in all four means: retained faint/dark +0.1607% / +0.0772% raw and +0.1072% / +0.0405% EMA; organic faint/dark +0.0846% / +0.0476% raw and +0.0802% / +0.0438% EMA. Band-error means fall slightly in both retained cohorts but rise slightly in both organic cohorts. These small numerical gains do not establish visible photographic-detail recovery.

Relative to the frozen V183 EMA initializer, mean mesh response rises 17.76% raw / 20.73% EMA, with quiet spatial RMS still 0.12–0.48% higher. Against V181 EMA, response rises 25.95% / 29.12%, with quiet spatial error 0.70–1.09% higher. Against V172 EMA it rises 34.82% / 38.22%, with quiet spatial error 0.73–1.15% higher. Against V180 EMA it rises 14.93% / 17.82%; quiet spatial error is slightly lower at ISO6400 and higher at ISO12800. These contextual comparisons also differ in capacity and training history.

V187 EMA exceeds V161 EMA's mean mesh response by 2.28%, while quiet spatial RMS is 5.51–7.83% lower on all 32 inputs. Only 69/256 present responses increase against V161; it is not uniform per-case superiority. Raw response is 0.24% below V161 with quiet spatial RMS 5.66–8.11% lower. The earlier optional periodic-detail correction retains higher average response and its known seam/false-wave costs. No model combines all strengths.

## Actual native inspection

All 60 figures, 12 noisy/restored/exact-GT triplets and 15 original sheets were actually viewed, with a second set of native focus sheets for V185/V187 comparisons. Every cell retains 160×160 pixels. On mesh seed2026112302 the amplified view shows small periodic-modulation changes; normal exposure is still weak. Seed2026112309 retains its strong orientation while the weak crossing family remains largely missing. Broad colored blotches survive in absent mesh and dark flats.

Main DSCF3879 sky remains visually smooth at exposure4. Building details and foliage remain soft; the coarse chain-link fence survives. Fine DSCF3842 cab mesh at exposure16 has small strand-modulation changes in both 160-pixel ROIs under nominal and profile3879 conditioning, without clear recovery of missing crossings. The ISO100/AHD and both SOOC JPEG panels remain independent qualitative references, not exact GT: aperture, exposure time, motion and processing differ. No pixelwise real-reference score is used.

Natural bird/branch, butterfly and organic detail remain soft. Amplified quiet step/bar/slant/stripe ROIs still contain false vertical or diagonal modulation and broad mottle; some faint modulation remains visible at normal exposure. The measured quiet gain does not resolve hallucinated detail. ADC gray, bark, fur and all four sloped-plane controls retain inherited pixels exactly.

## Source, checkpoint, noise and display

Both states use source checkpoint SHA256 `40b7c7c295ba82cc6b4a4646245483a3234de2759e2ae4d5a8e4e63a16a5e05a`. Raw module SHA256 is `3c61f8575b7c0ffa77bd42ba07ce17273d2f2d0fd36a4ba148a1ac578c24c012`; EMA is `4739e107a2460166dae5f14c7d89415b4b0c1ccc689d5a3480787ffa1696ebc4`. The final index binds strict full exports and all native manifests.

Representative mesh triplets use procedural seeds2026112302 and2026112309, RGGB, native ROI `[176,176,160,160]`, Poisson shot coefficient0.00128 and read variance6.5536e−6, exposure8, contrast1. Amplified boards use contrast40 around the same fixed anchor; no crop pixel is resized. Quiet ROI is `[80,176,160,160]`, exposure8/contrast40, with ISO12800 shot0.00256/read2.62144e−5. Main protected ROIs use `[176,176,160,160]`, exposure4. Cab ROIs are `[206,229,160,160]` and `[426,189,160,160]` within native context `[600,6260,768,768]`, exposure16. The manifests retain exact source/arrays, per-capture variance, CFA, white balance, display anchor and reference labels for every figure.

## Execution and interpretation

The fresh head starts from V183 EMA with V185's exact initial state hash, four trainable tensors, 508 parameters and 193 state tensors; all 189 inherited tensors remain frozen/eval. The same 1,000 cached rows give 900 updates, 3,600 noisy images and 100 ADC skips, with identical nine losses, masks, domain weights, LR schedule and Adam/EMA clocks. Genuine row-eight restoration continues at row nine without replay. Pooling both greens, 3×3 spectral smoothing, unique allocation and interleaved ranks change together; neither phase is a selection holdout, and selected powers are not calibrated confidence. Frozen V183 matching retains its original selections.

The training audit passes all rows, nine-term totals, masks and five checkpoint restores. The quality audit checks 1,644 outputs, 6,576 input fingerprints, exact V183/V169 replays, 144 ADC outputs and all 750 raw/EMA pooled-wave/support pairs. It independently recomputes 72 native RGB plus 72 wave arrays, 53,772,288 addition channels, 510 ordinary metric scalars, 72 wave RMS values and 278 Decimal means. Tables retain all 25 methods/20,550 rows/46 contrasts/1,722 cells; 3,425 means and 17,184 paired checks pass. No older source or receipt is replaced.

Peak CUDA allocation is about6.22GiB for training and2.79GiB for review. This is not a new 102MP speed result. All new outputs remain local under a bounded0.4GiB forecast; external inputs are read-only. Protected GFX families/JPEGs/siblings stay out of training; originals and /mnt/dataz are unused. The next architectural work must improve weak orientation/crossing evidence and local suppression of false waves; further whole-head contrast amplification alone does not resolve those failures.
