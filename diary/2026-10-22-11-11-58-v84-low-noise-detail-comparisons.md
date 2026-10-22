# Show V84 low-noise detail and condition gains

Recorded: 2026-10-22T11:11:58-07:00 (America/Los_Angeles).

The preceding turn made progress by completing the three-model reporting smoke
and launching the post-training evaluation queue. Revalidated the original
training owner and worker as live; V100 continues and the evaluation queue waits.

The current gallery's ISO12800 examples hid much of V84's actual improvement.
Rebuilt descriptive V84−V43 photographic comparisons from existing full-panel
case scores. Across 427 photos/four CFAs, mean sRGB gains are +2.30 dB ADC-only,
+2.01 ISO100, +1.40 ISO1600, +.57 ISO12800, +.33 shadows, +3.21 highlights and
+.96 legacy noise. Each of 427 source averages over all 28 condition/CFA
combinations improves. There are 24 adverse individual cases among 11,956.
Overall change is +1.54062 dB, paired source bootstrap95 [+1.46272,+1.62447].
This reflects source variation and different model training histories, not an
isolated architecture effect or training-seed uncertainty.

The later fresh FP32 V43 reference averages 34.89933467 dB, differing from the
original plotted 34.89934326 by only −.00000859 dB. The PSNR history remains
unchanged. Historical B4/B2 classical reference checks cover 35,868 rows,
260,184 numeric fields and 26,760 matching nulls; maximum metric difference is
7.6294e-6. An initial exact-equality assumption about the historical V43 mean
was therefore too strong; the report retains the actual values and distinction.

Rendered the same first two fixed validation examples at ADC-only and ISO100
on CPU/native256/B1/FP32, RGGB, zero procedural examples, alongside RawNIND
global/per-channel input-gain adapters. Training kept the GPU. Selected V43,
V84 and RawNIND-channel triplets for publication; each crop is native160 and
uses the same noisy/GT pixels and display transform. Viewed both comparison
boards at original resolution: 20 cells representing 12 source triplets.
V84 retains the paraglider's broad orange color and fine suspension lines that
V43 loses; building edges are substantially cleaner than RawNIND. High-noise
detail suppression remains visible in the original gallery.

The README now shows this more informative ISO100 comparison, while the model
guide includes ADC-only/ISO100 and the existing ISO12800 comparisons, with
full source/ROI/checkpoint/noise/display metadata. The new images use fresh
CPU-seeded observations and do not replace the full-panel CUDA scores.
[Comparison evidence](../docs/results/v84-v43-photographic-comparison-v1.json)
records both and preserves the adverse case counts. Source photos/caches are
read-only and all these validation sources remain outside training.

Reproduce the reports using `python -m demosaic quality` with both recorded
checkpoint paths, the common427 manifest and the one-condition protocols in
`.cache/current-quality-20261022-v1/low-noise-photo-v1/`, specifying
`--device cpu --precision float32 --patch-size 256 --batch-size 1 --limit 2
--synthetic-count 0 --rawnind /mnt/external/demosaic/references/rawnind` and a
fresh output directory. Rebuild the public boards with
`scripts/render_quality_comparisons.py` and each shipped condition manifest.
No new architecture, training intervention or broad real-photo/SOTA claim.
