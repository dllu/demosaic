# Both directional/interval arms complete the original budget

V78 and V79 have each completed all 4,000 planned updates and their training
owners have exited successfully. The independent boundary stage passed and the
fixed quality evaluation has started. This verifies training completion; image
quality and model eligibility remain pending. V43 stays the working reference.
[Bound checkpoints, source/input/RNG checks and retained states](results/directional-interval-original4k-training-complete-v1.json).

| Arm | Interval weight | Updates | Example draws | Final checkpoint SHA256 |
| --- | ---: | ---: | ---: | --- |
| V78 control | 0 | 4,000 | 64,000 | `26e43921d2f4f46b39d9385c8399699f9fe1f0294f34efa4e6da0d4ad9baa7c4` |
| V79 interval | 0.1 | 4,000 | 64,000 | `2f3e567e4bca7bf308f79d5e613d791d612e7d950c0cd64c9c21ac548aa1f11f` |

Each final state has 99 finite restoration tensors, 99 finite EMA tensors and
97 finite AdamW states with correct step counters/shapes. All 89 common
trainable model/EMA tensors changed from the genuine initializer; context
normalization buffers remain unchanged. The four scheduled checkpoints per arm
are retained, and all 25,800 new scalar parameters have nonzero first and second
optimizer moments at every retained boundary. The counts describe example
draws rather than unique-source coverage or convergence.

Both runs start with the exact genuine V63 EMA, identical local branch weights,
zero output heads, fresh AdamW/EMA/RNG and unchanged frozen official DINO.
All 176 sampled observation records match, including legacy and input hashes.
All 161 logged step/domain/common-LR/full-batch fingerprints also match.
Model configuration, final Python/Torch/CUDA RNG states, Torch version and
captured source bundle agree. Saved configuration differences are exactly the
interval weight, run directory and run-specific source/protocol snapshot paths;
the archived protocol bytes are identical.

The actual optional-loss route also checks across the entire logged history:
the candidate interval term appears only on Commons/native synthetic steps and
is absent from paired RAW steps. Independent NumPy FP32 arithmetic reconstructs
all 238 logged nonpaired total losses across both arms exactly. This verifies
sampled scalar accounting, not every unlogged intermediate tensor.

Equal sampled data and final RNG do not establish bitwise GPU reproducibility.
The [observed first-step base-loss difference](directional-v78-original4k-training-handoff.md)
remains part of this single-trajectory comparison. Its cause is not isolated;
source/scene bootstrap bounds do not estimate process or training-seed variation.

The evaluator requires successful exact training-owner exit and independently
verified final states before inference. It is now running the fixed primary
panels with both EMAs and a freshly evaluated V63 parent. Full427/procedural,
source sensitivities, hue/highlights, analytic and cached GFX panels follow the
[predeclared protocol](directional-interval-v78-v79.md). CPU saved-array audits
and the native boards with retained V43/RawNIND comparisons follow successful
evaluation exit. Actual viewing and publication/source checks remain required.

No automatic extension or promotion follows these finite training results. The
fixed numerical criteria and native color/detail/highlight review still apply;
only an eligible candidate gets a separate full-frame FP32/16-bit/timing review.
No final restoration-quality, speed or SOTA result is claimed by this report.
