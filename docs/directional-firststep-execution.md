# One-batch execution replay preparation

The observed first-step base-loss difference in V78/V79 remains unexplained.
A new diagnostic captures the genuine initial model and first selected clean
training input, then compares execution profiles without updating weights.
The CPU harness has passed; GPU replays are queued after the current review's
exact successful owner/child exit and all ten completed stages.
[Source, CPU results, original failure and frozen queue](results/directional-firststep-execution-preparation-v1.json).

This addresses reproducibility of future experiments. It does not change the
completed directional training, its failed camera criteria, the ongoing fixed
review, a model default or the working V43 reference.

## Actual CPU evidence

The real trainer initializes the genuine V63 EMA with the same seed51 and new
zero-head directional branch. All91 parent entries match exactly within the99
restoration entries; the branch and official frozen DINO hashes match the
original trial. Interception occurs at the first selected Commons batch, before
degradation or any neural forward, backward or update. The captured clean batch
is16×3×256×256. CPU placement and zero loader workers allow this capture while
the GPU evaluator continues.

A separate CPU-only check uses the first image's central64px slice, fresh CPU
noise and IEEE FP32. Two forwards/backwards produce identical losses,
predictions, auxiliary mosaics and all97 clipped trainable-gradient tensors.
All gradients are finite. Full model and frozen DINO hashes stay unchanged;
CUDA is not initialized. This checks the harness, not CUDA repeatability or
restoration quality. Neither AdamW nor EMA is updated.

The initial import failed before model/input/CUDA work because it referenced a
closure helper absent from the frozen review checkout. Its plan/source and
failure are preserved. The second version has self-contained JSON/hash helpers;
its frozen-package import, genuine CPU capture, two-pass check, Ruff and format
checks pass. No training or inference implementation was changed to recover.

## Fixed GPU comparison

After successful evaluator exit, generate the noisy CUDA observation once from
the captured clean batch. Its complete tensor hash must equal the actual
original first-training-batch hash
`b0ac985abbfa82a415e731e5094cb4f5ff31452e7ed7fbb4a7c39e870babcc7f`.
Any mismatch stops the probe. Replays then load that same saved input and
restore its recorded RNG states; original tensor strides are checked too.

Three profiles each get two fresh processes, with two unchanged forward/
backward passes per process at actual B16/native256/BF16:

- Original convolution benchmarking, without deterministic enforcement.
- Benchmarking disabled, without deterministic enforcement.
- Benchmarking disabled with deterministic cuDNN/algorithm enforcement and
  `CUBLAS_WORKSPACE_CONFIG=:4096:8`.

The third profile is a bundle of settings, not an isolated test of one flag.
PyTorch distinguishes benchmark selection from deterministic operations and
does not guarantee reproducibility across releases/platforms.
[Official2.14 reproducibility guidance](https://docs.pytorch.org/docs/2.14/notes/randomness.html).
Strict mode may reject operations such as differentiable bilinear interpolation;
the probe records that refusal instead of silently relaxing enforcement.
[Official2.14 deterministic-operation coverage](https://docs.pytorch.org/docs/2.14/generated/torch.use_deterministic_algorithms.html).

Each successful pass retains output and gradient identities; first-pass tensors
support independent per-tensor maximum/RMS comparisons across fresh processes.
Weights remain unchanged. Cold search time is recorded but is not a steady
throughput or batch-size benchmark. A passing one-batch replay cannot establish
long-run training determinism, isolate the historical difference's cause or
prove model quality. No new quality trial or execution default follows
automatically. Only owned serial children run, under24GiB CUDA allocation and
40GiB available-RAM/128GiB root-space checks.
