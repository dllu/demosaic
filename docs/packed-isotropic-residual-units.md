# RAW input and residual units: discarded CUDA diagnostic

Dividing the learned residual by32 reduces early loss overshoot, but this small
fixed-data test does not establish a broad learning improvement. No production
setting or trained model is adopted. The [complete result and independent audit](results/packed-isotropic-residual-units-CUDA-v1.json)
record all curves, sources and frozen code. Learned weights were discarded.

Four fresh models share seed51, all3,464,396 initial parameter values, the same
852 tensors and an exactly identical bilinear initial prediction on every
fixture. Each runs256 AdamW updates, constant LR2e−4/decay.01, clipping1,
CUDA IEEE FP32, contiguous NCHW, without AMP or TF32. All four arms are GPU
controls; the separate running CPU study is not reused as a GPU control.

The same16 actual production training batches8001–8016 repeat16 times:
64 fixed observations, seven Commons/procedural, four native-clean and five
paired B4 batches, native256 pixels. Noise, sources and ordering stay fixed.
Original domain losses retain their physical units. Paired MSE covers only
valid measured reference-CFA samples; that reference is not exact RGB GT.

The raw, input gain32 and known-shot/read input-companding arms repeat the
[input-coordinate methods](packed-isotropic-fresh-coordinates.md). The fourth
uses input gain32 and divides only the learned FP32 residual by32, leaving
the physical bilinear skip fixed. There is no new capacity, image-derived
normalization, inverse output transform, pretrained initialization or EMA.
The residual parameterization changes optimization; it does not preserve later
updates through compensating weights or moments.

At256 updates, ratios to the common initial full-fixture values are below.
Each cell is **original loss / MSE**; lower is better. These are training errors.

| Arm | Commons/procedural | Native-clean | Paired |
| --- | --- | --- | --- |
| Original RAW | 1.07826 / .92895 | 1.22989 / .99030 | 1.36577 / 1.12865 |
| Input gain32 | 1.05692 / .88874 | 1.15170 / .93381 | 1.19203 / 1.05743 |
| Input companding | 1.05791 / .97541 | 1.10436 / .98997 | 1.15434 / 1.06618 |
| Gain32 + residual÷32 | .97615 / .93472 | .99937 / .99575 | .99581 / 1.00109 |

The final row has lower original loss than the other arms, but native/paired
improvements over initialization are under.5%, paired MSE still exceeds its
initial value, and Commons/native MSE improve less than with input gain alone.
At64/128 updates its native/paired original losses still exceeded initialization.
This is evidence about early optimization units, not convergence, generalization
or photographic quality. GFX, validation and protected-final scenes were unused.

Nine focused tests verify unchanged initial signal across all CFAs, preservation
of16-bit changes, nonzero residual scaling, initial head-gradient scaling,
parameter/state identity, hook cleanup and invalid-input rejection. Independently
replaying1024 ordered finite training rows,96 domain mean reductions,27 inputs
and45 frozen guards passes; the exact GPU process has exited. Production model
modules, recipes and checkpoints remain unchanged.
