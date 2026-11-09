# Full quality review for V200

The [physical cross-scale support prototype](scale-supported-cfa-wave.md) is
fully trained and independently audited; its registered two-endpoint quality
review is now running. **Image-quality gains remain unproven.**
The [readiness evidence](results/v200-scale-CFA-quality-readiness-v1.json)
records actual CPU checks and process observations separately from the planned
model measurements.

[Completed training and viewer preparation](results/v200-scale-supported-cfa-training-completed-v1.json)
records 900 updates, the full five-checkpoint audit and a seven-state browser
fixture. The fixture reuses V198 pixels and is explicitly rejected by the
actual-quality verifier; it is not a V200 image comparison.

## Comparisons that will decide whether it helps

Both raw and EMA endpoints will run on all **822 existing matched inputs**:
present and absent meshes, quiet parts of mixed scenes, independent fresh flats,
natural faint/dark photographs, zero-noise inputs, and the protected real-photo
contexts. The full comparison retains eleven methods, including both V198
endpoints, V197 RAW/innovation endpoints, the V195 frozen anchor, quieter V187
and V183. Aggregate gains will be reported beside per-input wins/losses and
off-signal costs. A rising whole-mesh response does not establish recovery of
the weak crossing direction, so the two fixed directional examples remain.

Sixty native figures include twelve small noisy/restored/GT triplets. Existing
source coordinates, 160×160 crop pixels, display exposure, contrast anchor,
white balance and matrix are retained across methods. Every rendered panel is
checked against the saved prediction or source panel after saving. Actual
viewing and interpretation remain required after rendering.

The real-photo boards retain main-scene sky, building detail, foliage and coarse
fence (DSCF3879 ISO6400 / DSCF3880 ISO100), plus both fine cab ROIs under both
noise profiles (DSCF3842 ISO6400 / DSCF3835 ISO100) with both SOOC JPEGs.
Independent ISO100/AHD/JPEG references differ in aperture, exposure and moving
subjects; they are **qualitative references, not exact GT or pixelwise scoring
targets**. Both families, JPEGs and siblings remain excluded from training.

## What the preparation actually verifies

The new support-receipt suite and its frozen copy each pass **35 CPU tests**.
These include all four Bayer layouts; geometry, channel, dtype and rank-count
bindings; unchanged V198 context binding; bounded complex agreement; finite
nonnegative nominal trace; symmetric/positive-semidefinite covariance; and
zero-noise feature absence. Corrupted bindings and invalid actual values are
rejected. The mathematical and wrapper engineering checks from the earlier
34-test suite remain separately recorded.

The metric preflight replays **255 saved metric scalars on 36 V195 native
contexts**, all within 1e−10, while rejecting neural-module forwards. The input
preflight checks all **822 cached Bayer layouts** without reading targets. The
display preflight checks **52 earlier exact-GT panels / 3,993,600 RGB channel
values** against two display implementations. It writes no new images. These
are preparation checks, not new candidate-quality measurements.

The frozen review will bind the full 36-channel context, twelve new agreement
channels, all three amplitude/covariance geometries and the nominal interpolated
trace bounds. Raw and EMA must produce identical input-derived support. On all
750 noisy contexts, the old 24-channel context, physical synthesis basis,
selection, small-window support and innovation field must match the completed
V198 journal exactly. This separates a changed trained readout from accidental
changes to the retained measurement implementation. All 107 neural source files
match the prior V200 engineering snapshot.

Nominal fit covariance still omits selection and correlated anchor errors;
overlapping-window interpolation uses a conservative nominal bound. These
quantities remain descriptive support features, not calibrated confidence or
a guarantee against hallucinated texture.

## Execution and remaining work

The controller verified the original training PID and creation time as terminal,
the complete 900-update result and independent full trace/checkpoint audit.
The four-case measurement-only CUDA bridge passed without neural forwards,
and the two-endpoint review is running. It will subsequently run the independent
quality audit, eleven-method reduction,
two strict exports, directional projections and native rendering. An expired
observation does not restart a scientific prefix. Native viewing, browser
pixel checks, qualitative interpretation and publication follow separately.

The existing **2 GiB local trial budget**, 40 GiB free-space reserve and zero
new external allocation remain. Cached data and historical predictions are
reused in place. There are no new source/noise draws, parent/DINO inference,
RAF decoding, original-media/dataz reads or protected optimizer inputs. The
current trained choices and their costs remain in the
[V198 comparison](cfa-innovation-wave-comparison.md) until this review supplies
actual evidence.
