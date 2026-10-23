# Explicit training execution settings

The trainer now accepts `training_execution: deterministic-v1` for controlled
experiments. Two fresh CUDA processes complete six real mixed-domain optimizer
updates with exactly matching model, EMA, AdamW, Python/CPU/CUDA RNG states,
inputs, and logged losses. The default remains `throughput-v1`.

The implementation checks below used the recorded V63 study setup. Current
[V102/V103 training](quality-first-training.md) instead starts from V101 on the
88,477-source cleaned cohort; its own launch receipt binds the actual settings.

The genuine V63 initializer, official frozen DINOv3 ConvNeXt-tiny, original
4,000-update learning-rate horizon, B16/native256/BF16, channels-last layout,
and that study's Commons 84,867 / native 128 / paired 32 sources remain fixed. The first six
domains are Commons, native, Commons, Commons, native, paired. All 99 model / 99 EMA /
97 optimizer states and all 97 trainable gradients are finite; DINO remains frozen
and unchanged. Peak CUDA allocation is 7.33 GiB. These short updates are discarded
engineering checks, not improved models or image-quality evidence.

The CPU check uses the same genuine model at B1/native64/FP32. Four default
updates reproduce the archived pre-change control exactly, including model,
EMA, optimizer, RNG and best-validation state. Strict four updates match a 2+2
resume exactly and exercise all three domains. Tiny real validation runs on the
original targets; its scores are not quality comparisons.

## Configuration and resume

Add this to a new experiment's YAML:

```yaml
training_execution: deterministic-v1
```

For CUDA, set the verified workspace value before starting Python:

```bash
source scripts/env.sh
CUBLAS_WORKSPACE_CONFIG=:4096:8 uv run --no-sync demosaic train \
  configs/your-experiment.yaml --initialize /path/to/parent.pt
```

Strict mode disables cuDNN benchmarking, enables deterministic cuDNN and
PyTorch algorithms with errors rather than warnings, and requires that workspace
value. Throughput mode enables benchmarking and disables deterministic
enforcement. Both use the explicit backend precision API compatible with the
model's IEEE FP32 guards. Each invocation restores the caller's prior backend
settings on success or failure, including nested invocations.

Checkpoints record the policy and actual runtime settings: PyTorch version,
device type, backend precision values, benchmark/determinism flags and CUDA
workspace value. Resume rejects a changed policy; strict resume also rejects
different recorded runtime values before constructing the model. Old checkpoints
without the keys mean `throughput-v1`. To change policy, initialize a new run
with fresh optimizer/EMA/RNG instead of resuming the old trajectory.

The runtime record is not a complete hardware/driver/environment fingerprint.
Six updates and one CPU restart do not prove long-run or cross-platform
determinism. No closed quality study is rerun or reinterpreted; this does not
identify the cause of a historical process difference. The
[earlier no-update replay](directional-firststep-execution.md) remains a separate
diagnostic.

## Validation and timing

The focused training/execution tests pass 34 cases. The final CPU suite, including
the separate private-loader integration, passes 1,120 tests with 9 skips. Tests cover the
actual local-model optimizer/resume path, legacy checkpoint compatibility,
policy/runtime rejection, invalid CUDA environment refusal before CUDA
initialization, RNG preservation and caller-setting restoration. An initial
test failure exposed mixing PyTorch's legacy and backend precision APIs; the
wrapper now consistently uses backend precision settings.

The real-model replay freezes 228 files in an isolated worktree. Run
`scripts/preflight_training_execution.py prepare OUTPUT`, then its frozen worker
for the three CPU cases and audit before the two CUDA cases and audit. Use the
frozen worktree's `src:scripts` on `PYTHONPATH`; hide CUDA for CPU cases. The
separate `scripts/benchmark_execution_policies.py` compares warmed mixed-domain
training at the same fixed batch size. Policy timing must be assessed separately
from the older batch-size sweeps.

The completed four-process comparison uses balanced throughput/strict/strict/
throughput order. Every fresh run excludes 15 warmup updates and measures 45;
the measurement window contains 19 Commons, 15 native and 11 paired steps.
Observation hashing is disabled in all timing runs. Timing includes selected
data loading, augmentation, degradation, frozen DINO, forward/backward, clipping,
AdamW and EMA. It excludes initialization, warmup, validation, checkpoint writes
and the final state audit. All cases retain the original 4,000-step LR horizon.

| Execution policy | Mean native256 patches/s | Two-run range |
| --- | ---: | ---: |
| Throughput | 21.5803 | 21.4638–21.6969 |
| Strict | 12.6249 | 12.5993–12.6505 |

Strict throughput is **41.5% lower**, or about 1.71 times the time per update in
this fixture. These are two-run ranges on a shared machine, not confidence
intervals or a batch-size optimum. Both strict 60-update checkpoints also have
exact matching model/EMA/optimizer/RNG states and all 60 logged losses and terms.
Complete input hashes are checked separately in the six-update replay, rather
than in this timed window. Neither policy's discarded checkpoint is promoted.
Throughput remains the default; future controlled studies can choose strict
execution explicitly after budgeting for its measured cost.

[Plans, frozen source, CPU/CUDA audits, timing and 60-update state check](results/training-execution-mixed-v1.json).
