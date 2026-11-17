# Donor subharmonics and the complete long-schedule 20k review

Recorded: 2026-11-17T12:14:43-08:00 (America/Los_Angeles).

Both missed weak guides from the 16 retained synthetic donors were
second-harmonic selections. Testing exactly half of each original
frequency on the donor RAW recovered both, with final errors below
0.05 query bins. Query phase fitting and gate thresholds stayed fixed.
At ISO400 source 3 far, threshold 2 weak response rises from 3.42%
to 9.10%, with quiet RMS 2.9501 to 2.9502 DN16. At ISO6400 source 4
far, threshold 2 stays near 1.17% weak response. Threshold 0.5 raises
the weak response on that source with the high-noise quiet cost still
above threshold 2. All four synthetic and eight real boards were
opened. One coarse-fence guide changes. All cab ROI predictions
reproduce the pooled results exactly. The first donor harness assumed
square 256-pixel windows and failed on the saved 128-pixel crop. The
replay uses the recorded native rectangles, and both attempts are
preserved.
[Donor subharmonic report](../docs/donor-subharmonics.md).

The long-schedule 20k EMA completes its 110-input three-way review.
The independent audit reproduces 220 previous control arrays and
checks 288 material rows, 180 faint strata and all 26 native boards.
At the same training budget, the long schedule lowers faint fine-band
error on bark, fur, and wood compared with both V120 and the short
schedule. Grass and flat spot-check spatial errors increase. Mean
faint sRGB PSNR is down 0.19124 dB versus short, even as camera-RGB
PSNR gains 0.15853 dB. All 26 boards were opened. Fine cab crossings
remain incomplete. The 100k trainer has passed 23,000 updates, and
the broader photo panels continue.
[Matched checkpoint report](../docs/full-corpus-long20k-native.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Cab mesh map](../docs/gfx-green-mesh.md) ·
[Comparable PSNR coverage](../docs/performance-history.md).
