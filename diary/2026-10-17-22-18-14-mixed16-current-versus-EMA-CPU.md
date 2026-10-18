# Current versus EMA: only a small selected-photo difference

Previous goal turn made progress: independently audited and published both
GPU camera panels, completed the V73 native CPU preview/matched readback,
and reclaimed7.12GiB from byte-identical owned completed-evaluation copies.
Its871d28d commit is pushed and the worktree was clean at this turn's start.

Revalidated the exact live review controller2362748/1792295060.93 and full427
child2440656/1792298415.15. Child is running with recent appended records;
82,030 cases at first poll,90,875 later. SSD519.09GiB and RAM~69GiB available.
This is progress plus a verified wait, not a blocker or project completion.

Tested whether early EMA averaging hides a materially stronger current model.
New isolated CPU operator`compare_mixed_model_ema_cpu.py` freezes the same two
synthetic photo observations and four GFX512 contexts for each immutable2k/
32k-example arm, checks every source/input and first reproduces all12 existing
EMA F32 predictions bitwise. Only restoration parameters then change to each
checkpoint's`model` state, rather than its`ema` state. No optimization,
new model archive or CUDA use; the main review continues unchanged.

Actual frozen protocol:
`/mnt/external/demosaic/benchmarks/mixed16-current-EMA-CPU-v1/plan.json`, SHA
`a1ca38691adaf0aedba88c74c2ab14f586b3514d575183d98043b4e881a3e201`.
37 inputs/263 guards checked before/after. V72/V73 parent hashes remain8d67375e/
43c10f2a. All852/865 restoration tensors load exactly;852/863 differ from EMA
(two V73 state buffers do not change). Both actual policy paths infer the same
native inputs in IEEE FP32 CPU/NCHW. No DINO weight update or training occurs.

Photo sRGB PSNR EMA/current:
V72 parachute28.799728/28.954559 (+.154831), building26.001005/26.032902
(+.031896); V73 parachute28.793188/28.964081 (+.170893), building26.012023/
26.047800 (+.035778). Metrics use the240×240 interior after border8 and float64
error accumulation. These two fixed conditions are not a population estimate or
evidence that current weights are a better general inference policy.

Both matched photo/GFX boards were actually viewed at native scale. Differences
are small; heavy grain and weak foliage/fence remain. The independently
demosaiced DSCF3880 ISO100/f5.6 reference is not exact GT. Averaging does not
explain the large visible mature-model gap on these examples. Keep the original
EMA decay/inference policy for the full review and defer model/continuation
decisions until its complete quality evidence is available.

Independent saved-array audit checks all24 F32/PNG pairs,24 exact denoised
renderings,12 shared noisy/reference panels,36 copied unresized board cells
and32 metric fields; the actual CPU owner has exited. Rendering operators are
reused and their definitions are not independently validated. All source/input
guards remain unchanged, and both new operator/auditor pass Ruff. No redundant
unit tests or model trials were added for this read-only diagnostic.

Public report includes two exact-GT current-weight triplets per arm and GFX
foliage/fence, source/ROI/conditioning/display/checkpoint hashes, explicit selected
state keys, proper real-reference labels and credits. Receipt:
`docs/results/mixed16-current-EMA-CPU-v1.json`, SHA
`91d4c2146c9da13eb95156be470a7183fdf7db425efcaa5352f8972394d8c4da`.
The standing scene/siblings and protected-final remain outside training/scoring.
SOTA, decisive real-photo superiority and100MP/10s remain unmet/unproven.

Final readback finds maximum metric arithmetic difference7.11e−15; all eight
published image copies and12 local report links verify. Exact CPU owner
2510369/1792300544.4 has exited. Main review controller/child are still live
under the same creation handles, with98,974/136,444 full427 records and
0.32s append age. SSD519.05GiB. No need to restart or alter that verified job.
