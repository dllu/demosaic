# Trained mixed16 state: CPU restart preflight

Both genuine2k/32k-example parent states pass four additional CPU updates
versus a2+2 save/reload **bitwise exactly**. Model weights, EMA, Adam tensors
and parameter groups, best score, counters, Python/Torch CPU RNG and all four
loss/observation records match. This prepares a possible isolated continuation;
it makes no quality or continuation decision while the full review runs.

[Exact parents, state hashes, observations, counters, source guards and scope](results/mixed16-trained-state-restart-CPU-v1.json).

The test uses production `backward_groups`, Adam construction, LR assignment,
EMA update and checkpoint serialization. It restores the actual V72/V73
trained states, including852/863 populated Adam entries, then follows their
unchanged40,000-update schedule,500 warmup, IEEE FP32, EMA rule and effective16
through four B4 forwards. Model capacity and the genuine frozen DINO branch
remain unchanged. All16 saved training-only input fixtures are verified before use.

To bound CPU work, the existing observations at source steps8001–8016 are
cropped to native64×64 at their top-left Bayer-aligned origin. They cover
seven Commons/procedural, four native and five paired source groups. No new
images are loaded or augmented. Each branch advances optimizer2000→2004,
data8000→8016 and examples32000→32064. Ambient RNG is deliberately perturbed
before restoration; sentinel draws make missing CPU RNG restoration observable.
Each test's midpoint checkpoint is removed only after its exact final comparison
passes. All learned test weights are discarded; parent archives remain unchanged.

The14 existing `tests/test_optimizer_batches.py` tests also pass in5.42s,
covering the actual production training loop's stop/resume, source/noise
sequence, EMA/moments, layout guards and unchanged default path. The real-parent
test complements those fixtures; it does **not** exercise `train()`'s full
loader/degradation/validation loop, GPU kernels or CUDA RNG. It is not a
production-size throughput test, photographic result or new quality model.
All20 inputs/261 source guards remain unchanged and the actual CPU owner exited.
Ruff passes for the operator.

A separate read-only audit verifies all40 executed production modules are
byte-identical to the trained package, parent model/EMA hashes change after the
four updates, and saved counts, schedule, best score and all16 source-group
fingerprints are consistent. Exact final restart equality is executed by the
producer; this audit does not rerun training or recreate discarded final weights.

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  PYTHONPATH="$PWD/src:$PWD/scripts" uv run --no-sync python -P \
  scripts/preflight_mixed_state_restart_cpu.py \
  --prepare /mnt/external/demosaic/benchmarks/mixed16-full-state-restart-CPU-NEW
# Run the frozen driver printed/prepared above, with the same CPU-only environment:
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  PYTHONPATH="$PWD/src:$PWD/scripts" uv run --no-sync python -P \
  /mnt/external/demosaic/benchmarks/mixed16-full-state-restart-CPU-NEW/driver.py \
  --run /mnt/external/demosaic/benchmarks/mixed16-full-state-restart-CPU-NEW/plan.json
```

The [matched trial](packed-isotropic-mixed16-trial.md) remains stopped at its
first gate. Any next run must preserve the original2k archives/logs, resume
full state in separate directories and wait for completed quality evidence.
Matching the old160,000-example checkpoint would require10,000 effective16
optimizer updates, rather than8,000. No extension is launched by this preflight.
