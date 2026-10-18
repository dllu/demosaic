# Stream native RGB16 exports with lower peak memory

The matched quarter-horizon RAW study continues: no-DINO has completed 40k,
DINO reached 29,825 at the last check, and the exact owned quality, compilation
and corrected-grid controllers are alive and waiting in their existing sequence.
The independent fresh-coordinate CPU diagnostic has completed 48 updates per arm;
its first post-training full-fixture evaluation is still pending at update 64.
No training settings or frozen study inputs were changed.

Removed avoidable full-frame copies from `write_rgb16`. Input finiteness checks,
clipping, original dtype arithmetic, rounding and byte conversion now work on
128-row strips. Orientation uses a source view, without altering the source.
RGB16 TIFFs retain their description/color tags and sRGB ICC profile. Writes
replace the final destination only on success and clean up partial temporary
files after failure.

The retained benchmark at
`/mnt/external/demosaic/benchmarks/rgb16-strip-export-CPU-v1/`
has a predeclared plan, the old/new sources and tests, an executable driver, six
individual receipts and a final receipt. It uses the cached normalized DSCF3879
RAW to construct a deterministic three-channel precision fixture at 101.995852 MP,
with the same non-contiguous HWC layout as the inference CLI. This is not restored
RGB or a quality comparison. It uses no GPU or source hard drive.

Across three fresh processes per policy, peak worker RSS fell from median
3.470 GiB to 1.553 GiB. This high-water mark includes common source preparation;
the reported difference from pre-write RSS must not be interpreted as a direct
strip-buffer measurement. Write medians were 1.659 s versus 1.251 s, but ranges
overlap (old 1.006–3.767 s, strips 1.124–1.284 s) while other owned jobs ran.
No reliable speedup or end-to-end inference claim is made. Timings include
page-cache writes and atomic replacement, without explicit fsync.

All 305,987,556 decoded RGB16 channel values in every trial exactly match the
original rounding expression. All six decoded arrays have SHA256
`fb5890c3e5177e07fcc5ff2ccd5be661ff3e44f91f65ec123fbd13283d4c0593`.
Sources remain byte-identical; TIFF descriptions, sample precision and ICC
profiles were checked. TIFF container layout changes, as intended. Full TIFFs
were hashed and deleted after all-pixel verification; the audit evidence remains.

Validation: 76 focused tests passed, two CUDA-only tests skipped with CUDA hidden,
and Ruff/diff checks passed. Regressions include all camera rotations, signed/HDR
values, float32/64 half-code rounding, read-only and non-contiguous views, final
partial strips, late nonfinite inputs and failed writes preserving destinations.
The public report and JSON are `docs/rgb16-strip-export.md` and
`docs/results/rgb16-strip-export-CPU-v1.json`; the README links the report.

The SOTA/real-camera-quality and 100 MP within 10 seconds goals remain unmet or
unproven. This engineering change supplies no new model or quality promotion.
