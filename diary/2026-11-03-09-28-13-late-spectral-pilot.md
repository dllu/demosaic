# Late spectral innovation pilot

Recorded: 2026-11-03T09:28:13-08:00 (America/Los_Angeles).

The unchanged-weight V146 window transfer left fine mesh and organic detail
weak. The next question is whether learned soft frequency gains can carry RAW
innovation directly past the frozen RGB denoiser, with local evidence governing
where it appears. This is a hypothesis, not an explanation established by the
earlier negative experiment.

Implemented `LateSpectralDetail`:30,402 parameters/twelve tensors, tapered
affine-detrended packed256/native512 FFT frames, signed four-phase innovation,
frequency-neighborhood convolution and a dilated local support CNN. A fixed
signed Malvar synthesis adds the result after V143. Exact constant observed
phases produce zero correction with arbitrary learned weights; actual noisy
flat/mixed-scene safety still needs measurement. Neither gain is a calibrated
probability and the tapered noise proxy is not post-detrend covariance.

The 21 component tests passed in 4.25s, including an independent NumPy DFT/WLS/
synthesis calculation, constants on all CFAs, optimizer continuation, CPU RNG
isolation and CUDA parity. That actual terminal output was not saved as a log;
the preparation receipt records the observation and source/test hashes.
The ten-update CUDA smoke then passed, including a genuine 8+2 reload, all source
types, all 12 parameter gradients and exact frozen parent/DINO hashes. Peak
allocated CUDA memory was 3,178,908,672 bytes. A scalar-conversion warning in its
log is preserved; it did not stop training or affect gradient construction.

V147 production starts fresh for 1,000 updates/B4. Source probabilities are
mesh .35/weak .10/flat .15/mixed .15/photo .25. Procedural sources use native512 and
photographs native256, retaining 90,782 bin4→geometry→area2 photos and 27 reviewed
regions without stretching smaller inputs. Mesh/weak terms get 4× source weight;
pixel and small-gradient Charbonnier errors use input-noise units, with an
additional coefficient objective. This changes architecture, loss and source
distribution together and is not a matched causal comparison against V146.

The first preparation incorrectly rejected validation entries during its
heldout-exclusion assertion; it stopped before noise or network execution.
All 16 review photos are val-only in both manifests. Its bytes and failure
receipt remain under`V147-late-spectral-v1`. Corrected preparation/training is
`V147-late-spectral-v2`. The ten smoke input/parent batches are adopted by the
fresh production run rather than redrawing/reexecuting their inputs.

The fixed review covers both final raw/EMA endpoints on 766 cached cases, with
no short-context bypass. Separately prepared 32 new noisy analytic mixed scenes
test an exact quiet patch next to a step/bar/stripe under both noisy priors and
all CFAs. Their slanted-edge coordinate scope was clarified in a new receipt
without altering design/input/ROI bytes. All quiet ROIs were asserted constant.
Main and extra cached GFX scenes, both priors, foliage/fences/sky/buildings and
native JPEG references are in the planned comparisons; ISO100/JPEG are not GT.

The source-frozen postprocess controller is waiting for the full training
horizon, then will collect both endpoints, independently score/audit arrays and
render/audit native crops, including the new mixed controls. Human viewing and
interpretation remain pending. Production had completed 250 updates at the
[public evidence snapshot](../docs/results/v147-late-spectral-preparation-v1.json).
No trained gain, safety result, recommendation or inference integration is
claimed yet. V120 for general use and V143 with explicit periodic detail keep their
existing evidence and limitations.

See the [component and fixed-review documentation](../docs/late-spectral-detail.md).
All data access uses repository/external caches; no `/mnt/dataz`, original media,
or RAW decoding. Active jobs retain exact PID/create-time ownership, a 12 GiB CUDA
cap and host/disk reserves. The overall fine-detail/clean-sky goal remains active.

Continuation: independently reconstructed the32 mixed targets in NumPy Float64
and checked CFA placement, WB/matrix, exact quiet rectangles, ADC grid, bit-exact
variance maps and Poisson/Gaussian moments. Maximum target discrepancy is
0.02588333 DN16; maximum mean/second-moment deviations are3.0951/2.6588 standard
errors. No noise was redrawn and no network executed. The
[audit](../docs/results/v147-mixed-input-audit-v1.json) and
[byte-copy provenance](../docs/results/v147-mixed-input-audit-provenance-v1.json)
are public. These controls are valid for their declared synthetic purpose;
they do not prove trained quality. Training passed500 updates with the exact
PID/create-time owners rechecked live; the full1k review remains queued.
