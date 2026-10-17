# Review a fixed flatness-gated mean correction while original training continues

Tested one fixed packed33 window / three-standard-deviation flatness policy,
using the minimum gate across RGB and zero gate on ADC-white clipping. Add the
local observed-minus-predicted CFA mean to unchanged mature V60 output. Targets
and the low-ISO reference never enter the operator. No parameter search, model
source/default change, new training budget or GPU experiment.

The six saved CPU observations pass the small camera-RGB RMSE rule; photographs
are essentially unchanged. All1176 saved hue observations expose five of18
aggregate RMSE regressions. Bright saturated means improve, while centered RMS
usually worsens under high noise: saturation.5/peak.9 .002953→.004488. This does
not restore weak detail. Keep the method out of production.

Independent NumPy64 window/interpolation oracles on all four CFAs match exactly,
as do clean-constant/white-clipped/strong-texture limiting cases. Sixteen groups
of4096 Monte Carlo draws validate the iid unclipped moment-variance formula to
empirical/exact ratios .937–1.054. The formula does not prove confidence coverage
or unbiased restoration and does not model black clipping/ADC quantization.
All14112 hue metric fields independently agree within2.23e−16. Independently
replayed24 pilot camera metric scalars from saved arrays at publication.

Actually opened26 native triplets: twelve pilot, six full-grid and eight GFX.
All13 pairs have identical noisy/reference pixels, native160 panels and matching
ROI/WB/matrix/display. Published two exact-target photo pairs, one magenta pair
and corrected foliage/fence triplets. Four new genuine CPU-FP32 GFX forwards
share baseline/correction; input RAW arrays stay cached and no RAF is decoded.
Foliage/fence corrections are exactly zero in native ROIs; sky/building changes
are tiny and detail remains soft. Independent ISO100 AHD is not GT. The pilot
and hue grid require zero new neural forwards.

A separately predeclared CPU-only screen is running: first eight fixed protocol
photos plus all16 procedural sources, seven conditions/four CFAs,1344 method-case
rows. Owner PID3303654/create1792236330.75 is real and live at publication;
result.json is absent. No completion or native-review claim. Finish/review that
fixed screen without tuning this window/threshold; do not launch another copy.
Original V63/V64 20k schedules and their review owners remain live and unchanged.
Commons downloader remains live. Protected final scenes and cold originals were
not accessed.

Updated the pipeline overview to connect the three requested changes with their
existing measurements, and replaced a stale RAW-sweep queue paragraph with the
actual completed result. No new code tests for documentation/results publication;
validated all local Markdown links and unchanged copied PNG hashes. No claim of
SOTA, full427 replacement, latency improvement or model promotion.
