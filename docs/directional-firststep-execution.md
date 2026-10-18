# First-training-batch execution replay

The strict profile produces identical predictions, auxiliary output and all97
clipped gradient tensors both within and across two fresh GPU processes.
Disabling convolution benchmarking alone fixes the cross-process predictions
in this fixture but leaves14 clipped-gradient tensors different. The original
benchmarking profile changes both predictions and gradients.
[Complete results and saved-tensor differences](results/directional-firststep-execution-complete-v1.json).
[Source, CPU results, original failure and frozen queue](results/directional-firststep-execution-preparation-v1.json).

All six GPU processes completed after the exact successful reviewer exit and
all10 original stages. No weights, AdamW or EMA were updated. This addresses
future experiment execution; it does not change the completed directional
training/review, failed camera criteria, a default or the working V43 reference.

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

The noisy CUDA observation generated from the captured clean batch matches the
actual original first-training-batch hash exactly:
`b0ac985abbfa82a415e731e5094cb4f5ff31452e7ed7fbb4a7c39e870babcc7f`.
All replays load that same saved input, restore its recorded RNG states and
check original tensor strides, genuine initial-model and frozen-DINO identities.

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
Strict mode can reject unsupported operations in other paths; this actual
configuration completed both forwards/backwards without any downgrade.
[Official2.14 deterministic-operation coverage](https://docs.pytorch.org/docs/2.14/generated/torch.use_deterministic_algorithms.html).

## Observed differences

The99 saved tensors here are prediction, auxiliary mosaic and97 clipped
gradients, separate from the99 restoration state entries. First-pass tensors
are compared independently in FP64 across the two fresh processes:

| Profile | Prediction maximum / RMS difference | Different clipped gradients | All99 tensors exact within both processes? |
| --- | --- | ---: | --- |
| Benchmark enabled |.00419557 / .000165869|93|no|
| Benchmark disabled |0 / 0|14|no|
| Strict bundle |0 / 0|0|yes|

The maximum clipped-gradient difference is6.57421e-5 with benchmarking,
5.12431e-7 without it and0 under strict execution. Fresh-process loss changes
are6.05360e-7,0 and0, respectively. Equal scalar loss alone therefore cannot
establish equal gradients. Benchmark process0 exactly reproduces the original
V78 first loss. Full model and frozen DINO stay unchanged in every process.

This demonstrates execution-profile variation with the actual original input
and initialization. It does not identify a specific historical kernel or prove
the cause of V79's original difference, whose initial predictions were not saved.
The strict settings are a bundle; this is not an isolated test of each flag.
Cold search time is recorded but is not steady throughput or a batch-size sweep.
All exact owners/children have exited.

The later [optional execution policy and mixed-domain checks](training-execution.md)
complete exact six-update replays, matching strict 60-update states, CPU resume
and warmed timing. Strict throughput is41.5% lower in that B16 fixture; the
throughput policy stays default. This original one-batch check cannot establish long-run
determinism, model quality or portability across software/hardware versions. No
new quality trial or execution default follows automatically. Only owned serial
children ran under24GiB CUDA allocation and40GiB available-RAM/128GiB root-space
checks. The original single-trajectory quality caveat remains in force.
