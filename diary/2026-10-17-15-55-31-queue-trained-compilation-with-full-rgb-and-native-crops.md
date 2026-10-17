# Queue trained-checkpoint compilation after the quarter review

The three requested training-pipeline improvements remain implemented and
measured; this work addresses the later RAW model's unresolved inference cost.
No training, physical model math, precision default or source selection changes.

Added `scripts/benchmark_packed_compilation.py` and
`scripts/prepare_packed_compilation_inputs.py`. The local inference fixture
retains two fixed CPU-generated held-out photo observations, verifies four
saved GFX contexts against the locally decoded cached DSCF3879, and adds one
fixed all-CFA/low-high-signal analytic batch. It never touches source hard
drives or admits the GFX scene to training. Fixture SHA:
`11655660520041c0b9255f197758c6c313ef50834605dc78350c1e5c6f3d8784`.

The actual no-DINO16k EMA, SHA
`320c87cb4a357f9f86466ddd606d2b414ad4840cb8875690c5c222322e8289df`,
passed the final frozen executable's CPU photo preflight. Dynamo eager-backend
FP32 output is bitwise equal on both entire256px observations. All parameter
identities, state keys and tensor bytes, including the physical parts, remain
unchanged. This is not CUDA Inductor or a speed measurement. I inspected all
four native eager/compiled triplets; both policies agree, and substantial model
noise remains. Published them in the compilation note with full metadata and
source/license records. No claim of improved16k quality is made.

Six focused CPU tests passed in6.55s, and Ruff passed. The three new numerical
tests catch the final partial chunk, unclipped HDR/negative channels, globally
weighted RMS, constant small bias and nonfinite pixels outside usual ROIs.

Launched a CPU-only waiting controller, PID1892187/create-time1792277635.47,
behind the exact quarter review PID1784241/create-time1792275654.03. It has no
children and starts no GPU work until the review controller and actual training
owners exit successfully. Plan SHA:
`dd4dd08056978df8e0498dd4aa10fd8baa02a46d0e39921c5b684253da525a63`;
controller SHA:
`71e3d0d635c29782b1d49c90e784bec4eef25915e84908f358eb06a1162f813d`.
All159 frozen guards and19 inputs matched before launch and afterward.

The prospective study uses both actual40k EMAs, fresh separate photo256 and
serving512 workers, actual CUDA Inductor and unchanged eager FP16/physicalFP32.
It rejects patch accuracy above a predeclared1DN16 maximum or.25DN16 RMS before
full timing. Four shuffled model/policy cases use the full101.995852MP GFX RAW,
512/64/B4, one excluded warmup plus three timed restores. Every saved float RGB
pixel, repeat stability, RGB16 encoding and model-state identity is audited.
The final CPU stage generates16 native sky/building/foliage/fence triplets with
the separate ISO100 reference accurately labeled not GT. Timing excludes decode,
compile/warmup/export; existing disk compiler caches are retained, so first-call
wall time is not necessarily cold-cache code generation. No automatic policy
adoption or promotion follows. Manual native inspection remains required.

Public receipt:
`docs/results/packed-isotropic-compilation-queue-v1.json`, SHA
`33faedf34a27885fa36652eb757483092c4df0c97485a8eaa6ed446b28dd9082`.
Private root:
`/mnt/external/demosaic/benchmarks/packed-isotropic-compilation-workflow-v1`;
live status:
`/mnt/external/demosaic/runs/packed-isotropic-compilation-workflow-v1.json`.

At15:55 local, the original no-DINO continuation is at step27600. Its training
owner, serial quarter-review queue and original Commons downloader are alive.
DINO continuation and full40k quality/visual review still follow. PROMPT.md's
quality and speed goals remain unfulfilled; the working reference stays V43.
