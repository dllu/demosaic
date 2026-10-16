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
  describes separate RAW denoising, pretrained demosaicing and RGB denoising
  stages, with demosaicer pretraining followed by denoiser training. Only the
  primary abstract was accessible; detailed results/weights were not reproduced.
* [JD3Net, WACV workshop 2026](https://arxiv.org/html/2601.00703v2)
  uses downsampled isotropic trunks of simplified NAF blocks without channel
  attention. It studies width/depth/downsampling tradeoffs and supports testing
  compact convolutional alternatives. Its [official repository](https://github.com/cory-fan/jd3net)
  has no checked-in weights or root model license in the inspected tree at
  `47489cbe3eba746e13ad8be8898956d7895f1835`; the camera-pipeline subcomponent has
  a separate license. No upstream model code has been incorporated here.
* [FFNet, April 2026](https://doi.org/10.3390/math14071175)
  studies frequency-domain features for JDD. The
  [authors' repository](https://github.com/Donghui-Zhang2005/Demosaicing-and-Denoising)
  at `62be4ab8c6d859001b3523779f04387e2ef11ed7` has no license file or checked-in
  weights in the inspected tree. It is research context, not a claimed reproduced
  baseline. Neither repository limitation blocks our own ongoing training.
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
half sensor resolution on four spatial Bayer phases, four variance maps and 12
one-hot phase/color maps, with WB/matrix conditioning for highlight recovery.
It fuses projected DINOv3 intermediate features near its
bottleneck, with trainable zero-initialized gates. The decoder uses pixel shuffle
and a demosaic residual baseline (initially bilinear; V6 uses variance-adaptive
Malvar interpolation). Local paths retain fine geometry;
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

Later on the same day, the official endpoint returned HTTP 200. The genuine
21,596,544-parameter ViT-S/16 weights downloaded successfully. A CUDA BF16
forward/backward run verified finite reconstruction, a nonzero fusion-gate
gradient and no gradients on the frozen backbone. The HF revision is
`114c1379950215c8b35dfcd4e90a5c251dde0d32` and is pinned in the 8192-source
experiment and restoration checkpoints. The completed matched 20k-step control
shows a small positive effect across the 427-photo multi-condition validation
suite; see [the results and remaining failures](experiments.md).

The 2026 structural-guidance paper's linked repository returned HTTP 404 during
the follow-up survey, so no claimed reproduction or pretrained baseline is used.
Samsung's released implementation carries CC BY-NC-SA 4.0, incompatible with
the requested commercially usable pipeline. Neither observation establishes our
model's standing against those methods. The independently implemented Malvar
2004 filters provide an additional classical sanity check. They exposed the
earlier models' low-noise photographic deficit; V6 step20000 now exceeds their
mean ADC-only PSNR and SSIM in the declared 427-photo protocol, while separate
procedural stress patterns still expose weaknesses.

The follow-up real-noise evaluation survey inspected RawNIND's publisher catalog
and [paper's validation method](https://arxiv.org/html/2501.08924v2#S4).
The dataset is commercially usable under CC BY-SA 4.0, with additional per-scene
CC0 grants/credits in the publisher's permissions file. It contains paired
low/high-ISO RAW captures; geometric alignment, exposure matching and invalid
regions are material to scoring. The catalog's current `dataset.yaml` flags
identify 16 reserved Bayer scenes, including six unknown-sensor scenes. The
separate older `test_reserve.yaml` file does not enumerate that current reserve;
the acquisition pipeline uses descriptor flags and corrected filename prefixes.
Small development and untouched official-test subsets are now checksum-verified;
see [data selection and reference-unit caveats](evaluation.md#paired-real-raw-evaluation-sources).

## Follow-up on weak-signal representation

[Ke et al., CVPR workshop 2025](https://arxiv.org/html/2312.03640) compare linear
RAW/HDR training with perceptual input/output encodings and losses. Their results
motivate testing signal representation separately from numerical precision;
they do not establish which representation works best for our Bayer task. Our
matched BF16/IEEE-FP32 flat controls are close. The noise-unit RGB correction
branch is an independent experiment; it is not a reproduction of that study.

[YOND, June 2025](https://arxiv.org/abs/2506.03645) combines noise estimation,
expectation-matched variance stabilization and an SNR-guided denoiser. Its
[official repository](https://github.com/fenghansen/YOND_public) labels the code
MIT but states that core CNE/EM-VST modules are obfuscated pending acceptance;
weights are linked through Baidu Netdisk. No YOND code or weights have been
incorporated, and no reproduced baseline score is claimed. It remains useful
primary-source context for variance stabilization and calibrated noise handling.

The optional [DINO low-rank adaptation experiment](dino-low-rank-adaptation.md)
uses the original [LoRA construction](https://arxiv.org/abs/2106.09685) for
query/value updates, while retaining the pinned DINOv3 pretrained tensors.
CPU gradient/checkpoint/restart checks and a genuine-weight fixture pass; no
trained RAW quality or speed claim follows. The separate
[fresh matched DINO control](fresh-dino-ablation.md) is prepared to test the
current foundation branch without inherited JDD training history.

## Larger frozen DINO capacity candidate

After the negative V49 adaptation gate, the official
[ViT-B/16 model card](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m)
provides a separate frozen-capacity candidate. Its published dense-task scores
exceed ViT-S on the listed benchmarks; that is not RAW restoration evidence.
The authorized account can fetch genuine config/weights at revision
`5931719e67bbdb9737e363e781fb0c67687896bc`. Both are cached with hashes, including
the weights' LFS SHA256 verification. [Availability receipt](results/dino-vitb-availability-v1.json).
No model has been constructed, benchmarked or trained with those weights here.
A future matched trial must compare fresh initialization, quality, memory and
latency. V50 retains ViT-S and tests data membership alone.
