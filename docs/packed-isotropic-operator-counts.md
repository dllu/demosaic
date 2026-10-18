# Executed learned-operator counts

Repeated camera metadata contributes **3.1455% of counted Conv/Linear MACs
without DINO and2.1957% with DINO**. These counts identify a small arithmetic
target; actual GPU operator profiling should choose the next speed change.
No metadata-folding implementation is adopted from this check.

[Actual checkpoint/input hashes, executed operators and independent formula check](results/packed-isotropic-operator-census-CPU-v1.json).

The camera phase/WB/matrix features are spatially constant:24 of32 inputs to
the local stem, and96 of128 after rearrangement into the quarter-resolution
stem. In principle a separate implementation could replace much of these
constant-channel convolutions with small camera-dependent boundary/interior
contributions. Correct padding, finite precision, memory traffic and GPU kernel
efficiency would still need measurement; the potential MAC reduction is not
a runtime fraction or a bound on speedup.

Two completed checkpoints are counted: current V72 no-DINO step2000 and the
retained original V70 DINO step40000. Their training budgets and units differ;
this is an executed-graph count, with neither a matched quality comparison nor
GPU timing. Actual frozen observations are one native256 photo and four
native512 GFX contexts. All computations use CPU FP32 with CUDA hidden.

| Executed input | No-DINO learned GMAC | DINO learned GMAC |
| --- | ---: | ---: |
| Native256, batch1 | 14.401 | 20.630 |
| Native512, batch4 | 230.418 | 330.082 |

Both512/batch4 cases assign9.66368GMAC to the two input stems, including
7.24776GMAC for their constant metadata inputs. The raw core's270 Conv2d
and104 LayerNorm calls match an independent formula built from actual spatial
sizes, widths, block counts and kernel sizes. Formula components include both
stems,48 quarter-resolution gated blocks, four local gated blocks, six trailing
group convolutions, the upsampling projection and RGB head. All four executed
cases match the raw-core formula exactly. The DINO graph additionally records
its actual Conv/Linear/normalization calls.

Instrumentation leaves all RGB outputs bitwise equal to uninstrumented forwards,
with model tensors and Torch RNG unchanged. LayerNorm output shapes/byte sizes
are recorded, but excluded from the MAC sum. Functional physical filters,
rendering, elementwise operations, allocation and data movement are also outside
that sum. Reported output-tensor bytes are not unique allocation counts or
memory-traffic measurements. There is no GPU speed, quality or16-bit
equivalence result for a modified algorithm here.

The [current trained-quality results](packed-isotropic-mixed16-V72-camera-CPU.md)
remain separate: residual grain and a substantial gap to RawNIND persist.
The active matched training/review recipe stays unchanged. GPU profiling follows
the serial quality review, rather than competing with its owned GPU work.

Reproduce on a fresh output path:

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 uv run --no-sync python -P \
  scripts/count_packed_inference_operators_cpu.py \
  /mnt/external/demosaic/models/no-dino-packed-isotropic-mixed16-v72-step2000.pt \
  /mnt/external/demosaic/models/dino-packed-isotropic-b4-v70-step40000.pt \
  --inputs /mnt/external/demosaic/benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json \
  --output /mnt/external/demosaic/benchmarks/NEW-operator-counts-CPU
```
