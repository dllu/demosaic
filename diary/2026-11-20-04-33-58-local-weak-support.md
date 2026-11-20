# Check local support for the weak Bayer correction

Recorded: 2026-11-20T04:33:58-08:00 (America/Los_Angeles).

The [local support report](../docs/local-weak-support.md) compares frozen
inference on another 24 source-disjoint ISO6400 photo fixtures, with two noise
draws and six roles per source. The full weak posterior adds 2.135 points of
recovered contrast and lowers intact weak RMS by 1.576 DN16 versus the combined
check. It adds 0.307 DN16 luma RMS inside true gaps. The corresponding false weak
projection rises 0.088 DN16 and the continuing strong strand changes 0.0004 DN16.

Reciprocal green scores over 32-pixel centers and four 16-pixel subwindows, and
held red/blue scores with ring or exterior phase, fail to lower added gap RMS
on either 24-source evaluation at equal recovery versus uniform scaling. The
prior 24-source replay reproduces the published per-draw combined and weak
scores exactly. Providing the known support as a four-station blend lowers
added gap luma RMS from 0.289 to 0.008 DN16 at equal recovery. The diagnostic
motivates finding evidence of where the weak strand stops.

Numerical and native reviews are complete for this frozen crop study. Two new
exact triplets and the largest prior gap outlier were viewed, alongside all
12 boards for [the main GFX scene](../docs/gfx-qualitative.md) and
[the fine green cab mesh](../docs/gfx-green-mesh.md). The sky remains smooth,
coarse crossings remain connected and fine cab crossings remain incomplete.
The [PSNR history](../docs/performance-history.md) covers the fixed benchmark
panels. This replay supplies no new measurements on those panels.
[Frozen receipts and source hashes](../docs/results/local-weak-support-v1/publication.json).
