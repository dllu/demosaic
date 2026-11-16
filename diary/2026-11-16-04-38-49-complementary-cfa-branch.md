# Preserve V200 carriers and add complementary CFA proposals

Recorded: 2026-11-16T04:38:49-08:00 (America/Los_Angeles).

The preceding goal turn made concrete progress: the competing-orientation head
was trained and reviewed, with a real weak-increment gain on the fixed panel,
strong-response losses and higher full-image RMS. The next action follows that
evidence rather than treating the local gain as completion of the weak-detail
goal. A fixed four/four quota spends useful carriers on a different family.

The new `ComplementaryWaveStage` freezes the complete scored V200 EMA path and
its eight-carrier CFA bank, then trains a fresh 643-parameter head on additional
proposals from RAW-minus-V200. Proposals within a periodic 3×3 neighborhood of an
inherited carrier or its conjugate are discarded without refill. There can be
up to 16 CFA carriers across the two stages. Four new tensors extend the previous
197-tensor component to 201 tensors; only the new readout trains. Earlier matching/
pooled stages and all their history remain frozen. This is extra capacity and
900 further updates, together with a changed residual/proposal mechanism; it is
not an equal-compute isolated selector comparison. Distinct carrier bins do not
guarantee that the final learned correction preserves strong response.

The recipe retains the original V200 cache/pair units, seed, objectives, domain
weights, optimizer and LR schedule. Its initializer is the full scored V200 EMA
export SHA256 2bb4a05943b6e9c1eb31877d19058ca4a3fea723666510fbaa133554d6ef7d22.
No new training observations/noise are constructed; protected scenes/siblings
remain excluded and original media are not accessed. The new head starts at
zero with a fresh optimizer/EMA clock; the admission probe is never an initializer.

Actual CUDA admission verifies all 197 inherited tensors and 393,216 exact
four-CFA noisy/ADC output channels. ADC routing is also checked with a nonzero
new head. An actual full training-only batch supplies finite gradients on the
four new tensors/643 parameters and no frozen gradient. Peak CUDA allocation is
11,039,763,456 bytes. No optimizer update or parent/DINO forward is made by the
admission. Existing kinds retain their exact historical output/auxiliary/gradient
behavior after extracting the shared physical-carrier measurement helper.

Training is live and progressing. The standard review is queued on both new
raw/EMA endpoints, each compared with the same frozen V200 EMA. The controller
binds the exact scored export's checkpoint/endpoint/training-plan/V195 history.
The earlier same-initializer model-intervention guard remains unchanged. The
new evaluation mode checks every retained original scalar and available native
baseline array inside the actual forward before declaring numerical completion.
It requires no separate anchor forward. All 822 inputs/all 60 native boards and 12
triplets, both GFX scenes, foliage/chain-link/sky/building, both cab ROIs/profiles
and both JPEGs remain included. Independent real references are never GT scores.

The next worker will reuse all three immutable finite-wire caches. Gain 0 now
means the complete V200 EMA, while the original V200 gain curves keep their
V195-based definition. Both new endpoints compare to the same EMA control.
The paired reporter checks those exact zero points and all conditions; tests
reject silently substituting the old zero reference or omitting one endpoint.
Checkpoint prefix handling also explicitly supports the new complement readout.

A closed input-only diagnostic runs after the recipe/source snapshot is frozen.
It reuses the original closed eight-carrier selections after fingerprint checks,
selects extras from cached V200 residuals, then scores known geometry only after
all 384 selections are written. Three CPU/GPU bridges match integer bins and
exclusion masks. There is no neural forward or new source/noise draw. At the 400
prior, weak-fundamental proximity within 3 native DFT bins rises 26.5625%→76.5625%
far and 0%→35.9375% near. The inherited bank's proximity never falls in any role/
direction/profile, by construction. Added valid carriers average 3.82/4.89/5.60
per input at 6400/1600/400. Neither proximity nor carrier counts detect structure
or establish quality; noisy near-edge weak proximity remains 0%. The same eight
sources underlie all CFA/repeat/noise-profile views. No target enters selection.

Validation: 61 focused tests pass in 7.53 s, including all-CFA nonzero-baseline and
ADC routing, strict initialization/serialization, frozen-anchor evaluation,
recipe/control history and paired zero-point checks. Ruff passes; original
source-cluster summaries/paired intervals replay exactly. Current docs and README
link the live prototype without replacing the measured recommendations. Original
machine receipts and exact-byte compressed source/plan copies are preserved.
[Architecture, admission, proposal evidence and launch identities](../docs/complementary-cfa-branch.md).

Completion/review follow-up: 2026-11-16T05:20:08-08:00 (America/Los_Angeles).

Training completed all 900 updates and 100 ADC skips, and every committed row
passed the Adam/EMA/domain/frozen-state audit. The frozen hash is identical to
admission. Final checkpoint SHA256:
`07d6344285465f177a54b205911d0e8293e71f2fbe09e715e2b3960890a11640`.

The first quality review failed before saving any prediction because the anchor
verifier treated legacy receipt metadata as ordinary image metrics. The original
rows also include observation indices, output/intermediate array fingerprints,
replay flags, wave RMS and optional native bindings. This was an evaluator bug,
not evidence about trained quality. The failed review, edge waiter, traceback,
first export, original training package and all checkpoints remain preserved.

The corrected verifier explicitly checks the indices, complete output hashes,
all retained intermediate hashes/replay flags and wave RMS, as well as every
image metric and available native array. Unknown scalar fields still fail; no
numerical tolerance was loosened. A real cached-case0 preflight passes all 19
scalar checks, the complete frozen output fingerprint and intermediate receipts,
using the actual trained endpoint. The new tests include the full legacy schema,
wrong indices/intermediate fingerprints and changed native arrays.

The corrected review uses an explicitly sealed evaluator-only overlay: the
original training package is copied, only `evaluation/runner.py` is replaced,
and all 147 other original Python files match exactly. Model loading, inference,
noise/data, optimizer/checkpoints and original numerical sources are unchanged.
The corrected raw export is byte-identical to the first export (SHA256
`d189c957d267a4208b75fb94bc2ec743e52b8452ff1ac7fd89efcd40343af5dc`).
There is no training replay, source/noise refresh or model choice based on this
repair. The corrected standard review and dependent edge worker have new bound
plans/owners; both are live and the standard review is saving checked predictions.

Validation now passes 64 focused tests in 7.32 s and Ruff, including an overlay
test that keeps original numerical modules even when checkout files differ.
Original failure/launch receipts and the evaluator patch are archived byte-exact.
Actual complete numerical/native quality remains pending, and the goal stays
active. [Completion and recovery evidence](../docs/results/complementary-preparation-v1/training-completed-and-review-recovery.json).
