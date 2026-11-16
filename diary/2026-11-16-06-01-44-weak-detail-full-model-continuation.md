# Lower-noise complementary gains and full-model continuation

Recorded: 2026-11-16T06:01:44-08:00 (America/Los_Angeles).

The complementary fresh-noise review is complete: 1,152 observations, raw/EMA,
five gains, all 12 comparison boards/12 triplets and three curves inspected.
At 400/far, weak response rises 8.1401%→9.4336%, strong response
86.7407%→86.8823%, and quiet error falls 5.993460→5.978843 DN16. The weak
gain is +1.2935 percentage points, with exploratory paired eight-source bootstrap
95% interval +0.7433 to +1.9473; the quiet interval crosses zero. At 400/near,
weak response rises 4.8417%→5.3492% with slightly lower quiet error. At 1600/far,
weak response rises 3.1332%→3.5246%, but quiet error rises. Noisiest/near weak
response declines, and all 6400/1600 quiet means rise.

Most weak structure remains missing; no clear new complete crossings are visible.
The same eight sources underpin all profiles, rather than 1,152 independent
scenes. All 905,969,664 anchor channels and 14,155,776 full-forward bridge
channels are exact; weights/RNG remain unchanged. Publication checks 921,600
candidate, 3,686,400 retained-comparison and 2,764,800 triplet RGB channels.
Original receipt bytes and frozen analysis sources are preserved.

[Completed report](../docs/complementary-edge-response.md) retains these gains
with the [fixed-mesh/real-photo failures](../docs/complementary-comparison.md).
The `complementary` preset exposes the trained component with an explicit
checkpoint. Actual raw/EMA loading checks all 201 tensors exactly. V120 remains
the recommendation; README/current choices/research describe measured results.

The broader next test resumes the existing full-model V131/V132 RAW spatial
attention comparison: [execution and proof](../docs/raw-spatial-continuation.md).
All 106 original input/source checks and four discarded 16+2 checks are adopted
without replay. The original 14,549-step control prefix has model/EMA/Adam,
all 89 Adam clocks, the full input trace and Torch/Python/CUDA RNG. Installed
PyTorch's strict runtime matches. Only 5,451 control updates remain before the
fresh 20k spatial arm. All 20k clean/noisy hashes and first initial outputs must
match. Original source, data, loss, seed and 20k horizons remain fixed; DINO stays
frozen while the full restoration trunk trains.

The first new launcher stopped before model construction/noise/updates because
I placed outputs outside the old frozen package's permitted directory. That
failed prefix remains intact. The corrected v2 execution copies the numerical/
data package byte-for-byte and places outputs below its new work directory.
The actual copied safety function accepts both paths and rejects an outside path.
Controller 121044/create1794837453.44 and worker 121050/create1794837454.94 are
live. At first new step 14,550, all 91 model tensors and 89 Adam states/groups
restore exactly; CPU/Python/CUDA RNG matches before the first new noise draw.
LR 2.5653477379816604e−6 continues correctly within the original 20k horizon.
The archived publication observation completed 14,724 updates; the next prepared
input is 14,725. No old checkpoint, failed receipt or source is modified.

All new writes are internal; external data remains read-only, with new 96/64 GiB
admission/reserve and internal 128/96 GiB. The execution retains 52 GiB RAM
admission, 16 GiB CUDA cap, 32 GB runtime floor, two threads/nice10, 48h per
worker, no other-job signals and no automatic retry. Thirteen new focused tests
and twenty consolidation tests pass; Ruff passes. Full-model quality is still
unmeasured.
