# CUDA EMA measurement

The bounded comparison completed after the inference profiler and its exact
owner exited. Both actual10k checkpoints pass byte-identical CUDA updates at
all eight schedule positions. Isolated scalar/grouped medians are3.282/.400ms
for no-DINO and3.371/.393ms for DINO; two grouped kernels replace852/865
scalar kernels. The [completed execution analysis](mixed16-quarter-execution-profile.md)
records the traces, limits and next measurement. Production training retains
the scalar loop; no whole-step speedup has been measured.

[Frozen sources, plan, owners and executed CPU checks](results/mixed16-EMA-CUDA-queue-v1.json).
Live status:
`/mnt/external/demosaic/runs/mixed16-EMA-after-profile-v1.json`.

The [CPU study](mixed16-EMA-grouping.md) established exact arithmetic on actual
restoration states, while retaining per-tensor CPU operations. It did not
establish GPU equivalence or a training-speed benefit. The harness subsequently
measured the actual10k/160k-example no-DINO and DINO checkpoints serially.

Both the controller and CUDA worker require the exact inference-profile owner
and its final child to exit successfully. The controller verifies the two
profile results, trace hashes and CUDA activity, then reuses that profiler's
frozen CPU gate to independently revalidate both completed training boundaries.
The earlier training and quality-review gates remain intact.

For each actual checkpoint, compare the original hash-checked EMA function with
one named grouped `torch._foreach_lerp_` call. Use all FP32 restoration-state
tensors, including DINO's preprocessing buffers, at eight original schedule
positions with five updates per case. Start from saved EMA values and hold the
model values fixed. Require byte-identical states after every update and
matching output strides before timing. A mismatch is preserved as a rejection with no
timings; it cannot change the production loop.

Passing arms receive three warmups and ten balanced, shuffled synchronized
samples per method, with CUDA-event and wall timings, plus separate scalar and
grouped operator traces containing genuine positive-duration CUDA activity.
Source model and initial EMA values, checkpoint bytes and CPU/Python/CUDA RNG
must remain unchanged. Each owned child has a300-second limit; launches require
32GiB available RAM and500GiB free disk. No automatic restart or adoption.

This measures updates of prebuilt named states. It excludes checkpoint loading,
state transfer, traversal of a real model's `state_dict`, network work, data
loading and optimizer work. It cannot establish whole-step training throughput
or100MP inference speed. Whole-step timing remains necessary before adoption.
Shared-machine measurements cannot establish an idle hardware optimum.

## Executed preflights

The exact future worker passes two CPU preflights on no-DINO8k and DINO2k.
All16 cases match both saved hashes from the previous independent replay;
four CPU traces have no CUDA activities. Post-timing/tracing states remain
byte-identical and original state/RNG remain unchanged. CPU timings serve only
to exercise the measurement code.

An actual request for CUDA work is rejected against the current unfinished
profile before nonexistent input paths are read or an output is created;
CUDA stays uninitialized. Forty focused tests pass, covering named state,
signed-zero hashing, invalid inputs, mismatch-before-timing, source checksums,
unfinished/live owners and invalid completed-profile artifacts. Ruff and
whitespace checks pass. All387 unique inputs/source files across the four
frozen workflows still match. No source manifest, recipe or model changed.
