# Lower-memory native 16-bit export

TIFF export now validates and quantizes 128-row strips instead of allocating
full-frame floating-point intermediates and a full-frame RGB16 array. Clipping,
round-to-even quantization, camera orientation, color-space description and the
sRGB ICC tag keep their previous meanings. The source is never modified.
The temporary TIFF is atomically replaced on success and removed after a failed
write; an existing destination survives failure.

The [completed CPU receipt](results/rgb16-strip-export-CPU-v1.json) compares the
previous and new implementations in six fresh processes, three per policy in a
fixed mixed order, at 11,662 × 8,746 pixels (101.995852 MP). Each receives the same
non-contiguous HWC float32 view of planar RGB, as produced by the inference CLI.
The precision fixture derives three channels from the locally cached normalized
DSCF3879 RAW. It includes negative and above-one values but is **not restored RGB**
and supplies no model-quality evidence. No GPU or source hard drive was used.

| Export | Median peak process RSS | Write median | Write range |
| --- | ---: | ---: | ---: |
| Previous full-frame writer | 3.470 GiB | 1.659 s | 1.006–3.767 s |
| Strip writer | 1.553 GiB | 1.251 s | 1.124–1.284 s |

Peak RSS is the whole fresh worker's high-water mark, including common input
preparation. It is not an isolated strip-buffer measurement. Timings include
validation, quantization, TIFF writing and atomic replacement; input preparation,
inference and subsequent verification are excluded. Writes use the OS page cache
without explicit `fsync`. Training and a separate CPU diagnostic continued on
this shared machine. The timing ranges overlap; this establishes reduced peak
memory, without a reliable throughput improvement or a 100 MP inference claim.

Every one of the 305,987,556 decoded channel values in **each** trial equals the
previous clipping/rounding expression exactly. All six decoded arrays have SHA256
`fb5890c3e5177e07fcc5ff2ccd5be661ff3e44f91f65ec123fbd13283d4c0593`.
The source arrays also remain byte-identical. The audit checks a single RGB page,
16-bit samples, description metadata and a valid sRGB ICC profile. TIFF container
bytes differ because strip offsets/layout change; the pixel result is identical.
Full TIFFs were hashed and then removed after verification. Their receipts,
frozen code, driver and plan remain under the recorded external benchmark path.

The focused CPU checks pass: 76 tests, with two CUDA-only tests skipped. Coverage
includes all four camera orientations, float32/float64 half-code rounding,
read-only and non-contiguous sources, final partial strips, a nonfinite value in
the last strip, and preservation of an existing destination after write failure.
Ruff passes. The implementation is in [io.py](../src/demosaic/io.py), with direct
regressions in [test_rgb16_streaming.py](../tests/test_rgb16_streaming.py).

The running matched 40k trials and queued quality, compilation and corrected-grid
studies use their frozen source snapshots and retain the original writer. Their
evidence and timing scopes remain separate from this export-only change.
