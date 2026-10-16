# Retained full-resolution model: first inference profile

The retained V37 model spends roughly 78% of profiled device time in its RGB
restoration CNN and 9% in DINO context. Packing, data loading and full-frame
blending are outside this resident-tile probe. The next speed experiment should
target the CNN while retaining native FP32 precision and testing image quality.
[Profile receipt and source identities](results/full-rgb-inference-profile-v1.json).

The probe runs four fixed native 512px tiles from cached DSCF3879, using the same
input-only shot/read prior and camera metadata as the standing GFX review.
V37 EMA checkpoint SHA256 is
`2e79285ba72003417eb681cae2bc304106548c8a8d3235dd20a4ea7218ec332a`.
No reference image is loaded and no model weights change. It began only after
the owned V40/V41 training and full review finished. Other users' work was left
alone; this remains a shared-machine measurement.

Three warmup calls precede five timed forwards. Median CUDA time is 187.89 ms
for the four-tile batch, range 186.89–188.46 ms. This excludes decoding, model
loading, packing/transfer, output transfer, full-frame blending, rendering and
encoding. It is not a 100 MP timing. Three subsequent instrumented forwards
produce these inclusive CPU-annotation device totals:

| Range | Calls | Device ms over three forwards |
| --- | ---: | ---: |
| RGB CNN | 3 | 440.05 |
| DINO context | 3 | 52.65 |
| GAT inverse | 12 | 25.18 |
| Physical features | 3 | 10.51 |
| MHC | 15 | 6.16 |

These are selected ranges, not an exhaustive partition. Operator/kernel table
rows and corresponding device annotation rows are nested or duplicated and
must not be added together. Host time attributed to MHC includes synchronization
with earlier asynchronous work; it does not mean MHC itself takes that long on
the device. Timed and instrumented outputs match bit-for-bit.

The full-resolution first encoder stage inherits FP32 activations from the
physical head: each residual adds its FP16 convolution output to an FP32 skip.
Consequently, subsequent convolutions recast large native feature maps. The
trace also shows substantial elementwise and copy work. This suggests a
specific experiment: retain the original FP32 head for the final native skip,
but evaluate FP16 hidden activations in the first encoder stage. The subsequent
[V42 implementation and complete review](hidden-autocast-v42-review.md) now
cover ADC/weak-detail checks, full matched evaluation, native crops and repeated
full-frame timing. This numerical change is explicit and opt-in; the profile
alone does not establish quality preservation or the 10-second target.

The 12 MB Chrome trace, operator table, raw JSON and executed script are in
`/mnt/external/demosaic/benchmarks/full-rgb-inference-profile-v1/`. All current
physical and neural computations retain their existing precision policy.
