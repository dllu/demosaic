# Width folding preserves convolution algebra, but increases dense work

An independent CPU check of the genuine V63 EMA restoration trunk finds that
folding adjacent width pixels into channels is mathematically viable for its
stride1/padding1 dense3×3 convolutions. The dense representation uses twice
their MACs, four times their kernel storage, and the same activation element
count at even widths. This is a compute/precision diagnostic, without a CUDA
timing or photographic quality result. The serving model stays unchanged.

The recent [Pochimireddy et al. CVPR2026 paper](https://lumen-cvpr26.github.io/raw-to-raw-extreme-low-light-enhancement/assets/pdfs/paper.pdf)
studies RAW-to-RAW mobile video denoising. Section3.4/Figure9 restructures width
and channels for a Qualcomm NPU; its Table5 reports opposite timing effects at
different widths. Its10/12-bit ISP and FP16/INT16 deployment differ from our
joint RGB16/GB10 task. The inspected
[publisher project page](https://lumen-cvpr26.github.io/raw-to-raw-extreme-low-light-enhancement/)
labels code/data as coming soon. This October20 availability observation and
the cached PDF/figure hashes are recorded in the
[fetch receipt](results/mobile-raw-CVPR2026-availability-v1.json).
No publisher code, weights or data are incorporated.

## Independent operator check

For native width coordinate `x = 2X + p`, a horizontal kernel offset `dx`
selects packed offset `floor((p+dx)/2)` and input phase `(p+dx) mod2`.
The probe derives a dense3×3 kernel with2× input/output channels from this
index identity. Half its coefficient positions are structurally zero.
Odd input widths are zero-padded before folding and cropped after unfolding;
the original zero-padding behavior is retained at all boundaries. Bias values
are duplicated by output phase. The local wrappers leave the original
stride2 and transpose-convolution modules in place.

All64 genuine V63 EMA trunk tensors load strictly. Forty-eight selected-kernel
checks cover six real layer weights, even/odd widths, FP64/FP32 and contiguous/
channels-last input/weight formats. Maximum FP64 operator difference is
4.44e−15; FP32 reaches5.96e−6 in feature units. A separate nonzero-bias case
checks every padded boundary against NumPy cross-correlation. Independent
scalar summation reproduces that control within5.00e−16.

The actual whole trunk runs on generated native32/B1 FP32 inputs in both memory
formats. Maximum normalized-output differences are3.28e−7 and4.17e−7. These
are approximate arithmetic comparisons, not bitwise/full-model/RGB16 parity.
No DINO/measurement offsets, inverse stabilization, photographs or targets enter
these forwards. Both trunk class ASTs match the actual frozen spectral-training
source. CPU RNG remains exact and CUDA is hidden throughout.

The first probe incorrectly tried `module.double()` on the whole trunk; its
explicit FP32 head boundary rejected that fixture. The failed source is kept.
The corrected probe limits full-trunk replay to its supported FP32 execution;
the FP64 checks apply to the individual convolution operators.

## Executed compute census

Hooks record all64 convolution/transpose-convolution calls in the original
native32/B1 forward. Independent topology arithmetic reproduces every total:

```text
MAC per native pixel
  = 56 × 64² × 9             # residual convolutions
  + (4 × 64 + 64 × 3) × 9   # head/tail
  + 6 × 64 × 128            # stride2 and transpose2 modules
  = 2,117,568
```

These dense counts include padded-zero taps. They exclude bias, activation,
residual, packing, conditioning, DINO, physical transforms and output work.
For dimensions divisible by eight, target-size counts scale analytically from
the observed geometry; they do not require a target-size CPU forward.

| Trunk representation |MACs for B4/native512|Dense storage of58 affected kernels|
| --- | ---: | ---: |
| Original |2.22043T|31,264,704 coefficients|
| Local dense width fold |4.38932T|125,058,816 coefficients|

For100MP without overlap/padding, the original trunk alone accounts for
211.7568T MACs, or423.5136T operations under the two-operations-per-MAC
convention. The dense fold raises total trunk MACs by97.68%. Packing preserves
the representation's element count; the wrapper's extra packing/unpacking
allocations are not a measured runtime peak. A global representation could
avoid repeated shuffles, but it does not remove these dense convolution MACs.

Hardware scheduling can make an operation-count increase worthwhile; this
study supplies no GB10 evidence for that tradeoff. The result therefore does
not justify a production rewrite or a claimed path to10s. The existing full
spectral quality/native review and already queued CUDA probes continue first.

[Complete probe](results/width-fold-convolution-CPU-v3.json),
[independent array/census/source audit](results/width-fold-convolution-audit-v3.json).
Run `scripts/probe_width_fold_convolution.py` with CUDA hidden. Executed sources,
generated input/output arrays and prior attempts remain under
`/mnt/external/demosaic/experiments/width-fold-convolution-CPU-v3/` and its siblings.
