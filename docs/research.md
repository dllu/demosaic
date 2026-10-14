# Method research and design record

Research started 2026-10-14. Sources below are primary implementations, papers,
and vendor documentation. A recent publication is not itself evidence that this
project matches its performance.

* [DINOv3, Meta, August 2025](https://github.com/facebookresearch/dinov3)
  provides high-resolution self-supervised dense features and ViT-S/16 through
  Transformers. Use a frozen pretrained feature branch alongside a spatial
  restoration network. Patch tokens alone discard the sampling-phase detail
  needed for demosaicing. Preserve a direct packed-Bayer path and predict a
  full-resolution residual instead of decoding RGB solely from semantic tokens.
* [Official Transformers DINOv3 interface](https://huggingface.co/docs/transformers/model_doc/dinov3)
  supports intermediate hidden states. Feed a camera-white-balanced sRGB preview
  with ImageNet normalization to the backbone; keep the actual prediction and
  reconstruction losses in linear camera RGB. Freeze weights, not the adapters.
* [DINO-IR](https://arxiv.org/abs/2312.01677) motivates robust foundation features
  for restoration. It is older than the preferred research window. This project
  uses the newer DINOv3 backbone; that substitution requires an ablation, not an
  assumed quality benefit.
* [Structural Guidance for Unified JDD, August 2026](https://arxiv.org/abs/2608.09995)
  uses a noise/CFA-conditioned SwinIR stream, a frozen DINOv3-S/16 stream, an
  adapter, and RGB/clean-mosaic supervision. Its limitations include synthetic
  Gaussian noise, sRGB-derived mosaics, and foundation-branch cost. This supports
  the dual-path direction but does not establish performance on physical RAWs.
  Our implementation uses linear Poisson-Gaussian simulation, explicit spatial
  Bayer phases, native aspect ratio for DINO tokens, and multiscale gated local
  mixing with transposed channel attention at coarse resolution. It is a new
  experimental design, not a reproduction of that paper's scores.
* [JDD-LI, September 2026](https://www.sciencedirect.com/science/article/pii/S1047320326002191)
  was located during the survey, but its architecture/results have not yet been
  independently inspected. It is not used as implementation evidence.
* [Samsung unified demosaicing, ICCP 2025](https://github.com/SamsungLabs/unified-demosaicing)
  examines single, quad and nona Bayer. Our initial scope is ordinary Bayer,
  matching the named GFX, Leica Q2 and Sony a7R II cameras. Reject unsupported
  arrays explicitly instead of silently treating them as Bayer.
* [RawNIND authors' code and weights](https://github.com/trougnouf/rawnind_jddc)
  and [paper](https://arxiv.org/abs/2501.08924) are comparison targets. Record
  calibration, color/gain alignment, and source license before comparing.
* [NVIDIA Spark optimization guide](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/optimization.html)
  calls for profiling, reproducible benchmarks and locality, and explains UMA
  memory reporting. PyTorch CPU/CUDA tensors still have distinct allocations:
  do not pretend unified DRAM automatically aliases them. Stream tiles and use
  bounded batches/float32 output accumulation rather than full-image feature maps.

## Proposed model

A noise-conditioned, multiscale gated convolutional encoder/decoder operates at
half sensor resolution on four spatial Bayer phases, four variance maps and four
color-label maps. It fuses projected DINOv3 intermediate features near its
bottleneck, with trainable zero-initialized gates. The decoder uses pixel shuffle
and a bilinear demosaic residual baseline. Local paths retain fine geometry;
DINO supplies context, never fabricated training targets. Linear and rendered
reconstruction, gradients and highlight chroma losses address texture and fringes.
No adversarial/diffusion objective is planned: faithful recovery is the priority.

## Access observation

On 2026-10-14 the configured HF token could query model metadata, but fetching
`facebook/dinov3-vits16-pretrain-lvd1689m/config.json` returned HTTP 403, explicitly
stating that the account is not on the authorized list. Access has been requested
from the user, who confirmed that review is pending and authorized experiments
with other architectures and the data pipeline. Implement the branch and continue base training; never silently
substitute random foundation weights or describe a no-backbone run as DINO-trained.
