# Preserve gray ICC input mode

The completed V5 8x preparation has10,367 successful caches and one failure.
Inspected that failure: freely licensed SkiLines.JPG, modeL,3584x2390, valid912B
GRAY/XYZ Dot Gain20% ICC profile. The loader expands toRGB before applying the
GRAY profile, causing LittleCMS cannot-build-transform. This is a real input
mode bug, not a malformed image or a reason to discard its profile.

Added a narrow gray-profile branch to prepare_one:for L/LA/1 with embeddedGRAY,
retainL until native ICC->sRGB conversion; then existing linear binning. All
other RGB/profile and unprofiled paths stay equivalent; malformed or mismatched
profiles still reject. Generated a348-byte synthetic D50/gamma2.2 gray ICC test
fixture with LittleCMS2 (No copyright,use freely), with no photo data. All three
new grayscale-mode regressions fail on old code. All38 relevant preparation,
rebin,duplicate,protected-scene tests pass after the correction, including10
bitwise legacy compatibility cases. Ruff passes on modified core/tests.

Actual source replay independently reproduces old rejection and prepares both
4x/8x in `/mnt/external/demosaic/benchmarks/gray-ICC-ingestion-CPU-check-v1/`.
Direct native-L ICC transformation plus independent FP64 linear-bin arithmetic
agrees within1uint16 code over2,005,248 scalar values. Distinct codes54,238 at4x
and43,559 at8x;4x->area2 vs8x also within1code. Original bytes/mtime and completed
V5 manifest/error log hashes remain exact. Diagnostic caches are not screened
or admitted; V5 retains its one-error exclusion and immutable actual operator.
Public receipt is `docs/results/gray-ICC-ingestion-check.json`.

Checked all live final10000 model/review/profile/sweep/compiled-probe plans: no
repository src guard depends on current prepare.py. Those jobs import their
immutable archived source. This edit affects future ingestion only. No current
training data, checkpoint, source snapshot, original image, controller, quality
result or performance setting changes. V5 independent full-cache audit has
completed; three48-image content sheets were actually viewed and will support
a separate reviewed freeze/matching4x preparation.
