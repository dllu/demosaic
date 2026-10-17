# Grayscale ICC conversion before linear binning

The fifth Commons snapshot rejected `File:SkiLines.JPG` with `cannot build
transform`. The JPEG is valid 8-bit grayscale (`L`) with an embedded 912-byte
`GRAY` / XYZ profile named `Dot Gain 20%`. Ingestion converted its samples to
RGB before applying the gray profile, giving LittleCMS the wrong input mode.
Pillow requires the profile and input color mode to correspond.
[ImageCms documentation](https://pillow.readthedocs.io/en/12.3.0/reference/ImageCms.html#PIL.ImageCms.profileToProfile).

Future ingestion preserves gray samples as `L` when a gray profile accompanies
`L`, `LA` or bilevel input. The ICC transform produces sRGB, followed by the
existing linear-light binning into uint16 caches. Other inputs keep the existing
RGB conversion path. Malformed profiles and RGB/gray-profile mismatches still
fail; no profile is silently discarded.

Three gray-profile regressions fail on the old code and pass on the correction.
Ten compatibility cases preserve the old RGB-profile and unprofiled output
bytes across RGB, RGBA, palette, grayscale and grayscale-alpha input. The
synthetic D50/gamma2.2 test profile was generated with LittleCMS2 and contains no
photo data; its copyright field permits free use. The preparation, rebinning,
duplicate and protected-scene tests pass: **38 tests**.

[Actual source replay and cache receipts](results/gray-ICC-ingestion-check.json)
reproduce the original rejection, then build 4× and 8× caches in a separate
diagnostic directory. They contain 54,238 and 43,559 distinct uint16 codes.
A direct native-gray ICC transform followed by independently computed FP64
linear-light binning agrees within one code over 2,005,248 scalar values.
Reducing the 4× cache by area2 also agrees with the 8× cache within one code.
These checks cover this source and numerical path, not all ICC profiles.

The source bytes and modification time remain unchanged. The frozen fifth
snapshot's manifest and one-error log remain unchanged; its cached targets
were produced by their archived original operator. The two repaired diagnostic
caches are not protected-scene screened or admitted to training. The running
model and its queued reviews use their existing frozen source packages and
manifests. This correction applies to future ingestion.
