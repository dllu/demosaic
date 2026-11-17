# RAW guide cross-check and 427-photo faint ADC audit

Recorded: 2026-11-17T15:40:04-08:00 (America/Los_Angeles).

The 427-photo faint ADC comparison is complete for V120 and the annealed
full-corpus 20k EMA checkpoint. The raw Corpus20k model gains 0.00708 dB mean
sRGB PSNR over V120 and has higher weakest-band error. Applying the calibrated
ADC-bin projection lowers Corpus20k's weakest-band RMS from 2.594 to 1.901
DN16, effectively matching V120 with the same projection. The improvement
holds on 297 of 326 sources with eligible weakest-band blocks. Both synthetic
triplets use exact targets and native pixels. I viewed the eight real boards
again after verifying exact bypass on the six positive-noise inputs. This
panel remains separate from the standard PSNR history, where the Corpus20k
full photo result is pending.
[Faint ADC report](../docs/full427-faint-adc.md) ·
[Standard PSNR history](../docs/performance-history.md).

I tested checking any proposed donor frequency move on two disjoint discovery
subsets before independent outer confirmation. At matched quiet RMS, ISO400
near-edge recovery with nominal guides rises from 3.94% to 4.35%. With shifted
far-edge guides it falls from 22.33% to 19.92%. The first independent verifier
missed a circular phase index at a floating-point boundary. The corrected
verifier reproduces the nested scores from the original saved predictions.
Both standing real-scene families were viewed. The sky equals V120, and the
cab mesh still lacks fine crossings. V120 remains the recommended model.
[RAW guide cross-check report](../docs/phase-guide-crosscheck.md) ·
[Standing GFX scene](../docs/gfx-qualitative.md) ·
[Fine green cab mesh](../docs/gfx-green-mesh.md).
