# Directional/interval engineering checks and launch

The [predeclared V78/V79 study](directional-interval-v78-v79.md) has started its
complete4,000-update arms serially. This is an implementation/execution result,
not a model-quality report. The
[byte-bound receipts and process identities](results/directional-interval-engineering-and-launch-v1.json)
identify both preflights, frozen training/review sources, exact initializers and
the queued evaluation. No checkpoint has been promoted; V43 remains the reference.

The full CPU suite passed1,059 tests with nine skips in104.36s. Four additional
signed/near-black constant-scene invariants were then added; the focused
directional/interval suite passed all30 tests in5.49s. The existing22 source
sensitivity tests passed after adding the new review status. Ruff and
`git diff --check` passed. The new implementation remains opt-in; zero interval
weight and a disabled branch preserve the old loss and model behavior.

The genuine V63 CPU preflight ran four actual Commons/native/paired updates for
each arm at B1/native64/FP32, plus a separate2+2 interrupted interval run. The
uninterrupted/resumed model, EMA, AdamW, Python/Torch/CUDA RNG, best state and step
match exactly. All four legacy/input observation hashes match across arms.
Common EMA initialization is exact; branch construction preserves common RNG.
The initial enabled/disabled predictions match exactly. The official DINO
weights remain frozen with SHA256
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
There are99 model tensors,99 EMA tensors and97 finite AdamW states.
Two additional genuine-checkpoint negative resume checks reject changing
interval weight to0.2 or branch LR multiplier to10. Both raise the intended
recipe-mismatch errors; the checkpoint SHA256 remains unchanged and CUDA stays
uninitialized.

The CUDA preflight ran six actual updates per arm at the intended
B16/native256/BF16 setting with4+2+2 data workers. Both initial predictions
exactly match the genuine parent; all12 pre-step checks find97 finite gradients,
and all six legacy/input observation hashes match. Common initial weights,
local branch initialization and frozen DINO match across arms. Maximum CUDA
allocations were9,257,002,496 and8,161,591,296 bytes. These fresh-process execution
checks include startup effects and do not establish a stable throughput or
memory difference between arms. The allocator quota was restored afterward.
All preflight updates and their tiny validations are discarded.

The production trainer is using the intended25,800 added parameters,
32,930,504 trainable parameters and60,750,632 total parameters. It has a
217-file frozen checkout,24GiB CUDA cap and three-hour per-arm timeout. The
separate217-file review checkout has identical package bytes and validates the
final4,000-step checkpoint lineage. Its controller waits for the exact training
owner and child to exit successfully. The review will then run fresh FP32
primary panels for both arms **and the actual V63 parent**, plus the fixed color,
texture, GFX and source sensitivity panels. Numerical and manual native-pixel
closure remain required afterward. No automatic extension, retuning or promotion.

The requested augmentation order, selected-domain loading and measured B16
choice remain in use; their completed results are in
[training pipeline work](training-pipeline.md). The Commons downloader remains
stopped at its storage reserve, and all training manifests stay frozen.

The [first1k state audit and independent review preparation](directional-interval-review-preparation.md)
now confirm nonzero optimizer moments for every new branch parameter and add
matched V43/RawNIND native comparisons to the queued final review. Quality is
still pending.
