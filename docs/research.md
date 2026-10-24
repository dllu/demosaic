# Method research and design record

Current implementation: V104's pretrained DRUNet RGB restoration with an official
frozen DINOv3 ConvNeXt-Tiny pyramid in V84's architectural family. Its completed
full427 result reaches 36.80085dB, +.12134dB over V102, with stronger known-camera,
material and weak-texture results. V102 retains lower ADC flat-color bias and a
higher unseen-camera mean. All seven panels and complete GFX exports are done.
See [current models](current-model.md), [completed V104 results](v104-reviewed-corpus-quality.md)
and the [active loss-scale trial](loss-scale-training.md).
The literature/design record below explains the explored approaches; its older
study decisions do not freeze the current architecture or README examples.

The current [V104 conditioning study](noise-conditioning.md) repeats the
fixed-strength comparison on twelve exact-target observations and six standing
GFX contexts. Lower conditioning retains more fine structure and grain while
losing high-noise PSNR; the nominal protocol remains unchanged. A local
same-capture sky check finds noise scale close to the supplied profile.

Earlier [V101 path/preview diagnostics](v101-conditioning-study.md#which-path-responds-to-conditioning)
make132 actual CPU restorations on the fixed material inputs. Lower CNN sigma
retains structure and grain while losing high-noise PSNR. Scaling DINO offsets
or substituting Wiener/self/clean-oracle previews gives no consistent gain.
This is a fixed-weight result, not a trained-backbone/fusion ablation; the
unavailable clean-image oracle is never a candidate method. Current quality
work continues from V104 on the further-cleaned corpus; its fixed endpoint
has completed its material/detail and full evaluation.

The [larger frozen ConvNeXt check](convnext-small-capacity.md) now pins official
Small weights and verifies compatible native feature shapes. A direct backbone
swap loses quality on four material cases. Resetting the fusion gates gives
Tiny/Small an exact common starting function, and both pass eight discarded
CPU optimizer updates with matching initial prediction/loss and batch hashes.
This prepares a later capacity comparison; V104's completed result now informs initialization.

The cleaned 90,864-source Tiny/Small recipes now pass separate eight-update
CPU and CUDA/native256/B16 checks, with exact initial identities, matching
observations and finite states. Their production runs remain unlaunched while
V111/V112 has priority; later capacity work can use the best completed initializer.
The [loss-smoothing diagnostic](loss-smoothing-detail.md) also measures 324
output gradients on 108 fixed V102 training-source restorations. Smaller epsilon
strengthens low-noise faint-detail slopes but increases the full gradient more.
The [active V111/V112 trial](loss-scale-training.md) tests .001 versus .0003 from
the original V104 EMA on the cleaned corpus, preserving its architecture and
learned fusion gates. Actual CPU/CUDA checks pass. V111 completed20k and
[improves all twelve material cases](v111-early-quality.md), with small GFX
changes. Its complete camera panels show −.01336/+.02006dB known/unseen changes
versus V104, with5/5 unseen scenes improving but persistent dark-field blotches.
V112 has also completed20k and full matched quality evaluation is running. The trainer exposes an
[explicit reconstruction-epsilon option](loss-smoothing-detail.md#configurable-training-scale)
with exact default/gradient replay and resumed-training checks. Production
defaults and existing frozen recipes remain unchanged.

The [optional eight-view inference study](dihedral-quality.md) now measures
uniform averaging of exact sensor rotations/reflections with the same V104
weights. It improves twelve fixed material cases and two adverse camera crops,
without repairing all fine detail/blotches. Production CPU/GB10 and RGB16/DNG
checks pass; full panels and complete 102MP policy results remain pending.
The completed [V111 analytic grids](v111-early-quality.md#complete-weak-texture-and-flat-color-panels)
also show better high-noise color/coarse carriers and worse ADC flat bias.

Research started 2026-10-14. Sources below are primary implementations, papers,
and vendor documentation. A recent publication is not itself evidence that this
project matches its performance.

The [late RGB/shared-path component diagnosis](late-rgb-component-review.md)
finds that the two main low-contrast4px ADC losses are already present before
the new head. Direct late-head effects and frozen prompt pooling barely change
them. Genuine capture/inverse/head parity, all32 native cells, prior-scalar
replay and independent direct RGB projections are complete. This supports
testing preservation of the mature shared path during refinement training;
it does not prove that freezing improves quality or rule out training-gradient
effects from the head.

The resulting [prospective V92 head-only intervention](late-rgb-head-only-v92.md)
holds all common model/EMA tensors exact while learning only the existing
global head. Its [engineering checks](late-rgb-head-only-engineering.md) cover
gradient isolation, actual mixed-data updates and fresh-process restart.
Completed V90 is explicitly a fixed historical exploratory reference, since
its outcomes informed this choice. Freezing remains an unproven quality
hypothesis at launch; inference architecture and working defaults remain unchanged.
The [completed original4000 quality/native review](late-rgb-head-only-original4k-review.md)
now rejects V92: photo PSNR falls.16213dB and unseen CFA PSNR falls.34470dB
versus V63. All125 native cells are viewed. Common model/EMA bytes stay exact,
and ADC preservation improves against historical V90, but both high-noise
carrier/flat contrasts fail. Freezing the entire common path does not supply
the requested quality benefit. It does not identify which common module or
training gradients caused the previous adaptation's losses; finer localization
would be a separate diagnosis. No training extension or promotion follows.

The [mature mixed-precision follow-up](mature-mixed-precision-engineering.md)
separately checks the existing autocast policy on actual V43/V63 weights,
including their different frozen DINO encoders. Genuine CPU execution and
independent code-sensitivity checks pass. The
[completed bounded CUDA pilot](mature-mixed-precision-pilot-review.md) now passes
the fixed accuracy/native screen after all V92 owners exit. Hidden FP16 is
4.250×/4.060× faster on resident four-context medians, with all48 actual native
cells,95.9million physical differences and3,840 analytic fields independently
checked. It is selected for separate full-quality/100MP qualification; no
full-frame or default change follows from this finite screen.

The [October20 PixIE follow-up](research-pixie-followup.md) records a recent
semantic-routing candidate and its differences from our current fusion.
The accompanying [CPU noise-proxy study](stabilized-noise-proxy.md) checks a
specific physical assumption first; neither establishes a new model result
or changes the live spectral comparison.

The [October20 width-folding follow-up](width-fold-convolution.md) checks a
recent mobile RAW deployment idea against the actual V63 trunk. Independent
CPU operator algebra and a64-layer compute census show approximate FP32
agreement but97.68% more dense trunk MACs. The paper's NPU results do not
establish a GB10 speedup; no production rewrite or new GPU job follows.

The [October20 WGCAN release check and CPU transfer pilot](wgcan-raw-mhc-cpu-pilot.md)
pins a recent wavelet/color-guided joint-restoration release and strictly loads
its genuine294-tensor checkpoint. Its learned ISP RGB target differs from our
linear output, so the fixed pilot uses its RAW branch followed by Malvar.
All24 native cells are actually viewed; the selected transfer has stronger
periodic texture and lower scores on both photos than stored V43. This is not
the publisher's joint RGB benchmark or an architecture ranking. No license
file/header was found in the pinned source, which remains an isolated reference;
there is no production incorporation or new GPU job.

The [CPU censored-highlight counterexamples](censored-highlight-gradients.md)
isolate two constraints in the current implementation: a constant-preserving
RAW head has no censored-channel offset, while hard display clipping can hide
a remaining color error even after adding that freedom. A pre-clipping interval
term supplies a gradient in the fixed fixture. This motivates a separate
prototype; it is not a trained-model result or a cause assigned to V77.

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
  The independent [RAW-native isotropic prototype](packed-isotropic.md) now
  rearranges packed CFA samples into quarter-resolution features, keeps a
  half-resolution phase-detail path and fuses genuine frozen DINOv3 ConvNeXt
  features. Production-size mixed-data/checkpoint checks passed. The
  [first32,000-example review](packed-isotropic-first32000-review.md) finds weak
  restoration close to bilinear; neither fresh endpoint is promoted. This is
  only5% of the original training horizon. Separate small-block compilation reduced synthetic forward time,
  with no full-frame speedup or trained-model precision claim.
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
  The [October 18 compatibility inspection](results/unified-demosaicing-CPU-preparation-v1.json)
  pins `d17aa7ebba5730c6259d256da028a84c521007c7` and verifies four published
  ISO400/800/1600/3200 checkpoints against their Git blob hashes. Each strictly
  loads all 336 state tensors into the original 3,203,107-parameter model.
  Artificial native48 CPU inputs give finite, exact repeated outputs with
  state/input/RNG unchanged. Its input is a mosaic plus three color masks,
  normalized by the publisher's 13,496-code range into −1..1; its three-pattern
  interface returns separate RGB tensors. This establishes compatibility only.
  The [repository license](https://github.com/SamsungLabs/unified-demosaicing/blob/d17aa7ebba5730c6259d256da028a84c521007c7/LICENSE.MD)
  says CC BY-NC-SA 4.0, while the main model header says CC BY-NC 4.0.
  Publisher code/weights stay in an isolated reference cache, outside the
  production implementation and training. Photo quality, transfer of the fixed
  ISO profiles to our cameras and separate weight terms were unverified at that
  compatibility boundary. The subsequent
  [fixed-default CPU pilot](unified-ISO3200-CPU-pilot.md) completes six saved
  observations and 30 native comparison cells. It retains grain and structured
  texture under the explicit integer-range/profile transfer; no promotion or
  general architecture ranking follows.
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
The [matched current-architecture capacity trial](fresh-dino-capacity.md) has
now passed genuine CPU/GPU initialization, gradient and portability preflights
and completed the [first1000 trained review](fresh-dino-capacity-1k-review.md),
[whole-state continuation to3000](fresh-dino-capacity-3k-review.md) and
[original10000 schedule](fresh-dino-capacity-10k-review.md).
No-context leads photographic PSNR at10k; neither ViT-S nor ViT-B improves its
photo mean. All three improve their own3k full-photo scores, but selected late
fabric color errors prevent promotion. This finite single-seed comparison does
not establish convergence or a universal foundation-model effect. Native
comparisons and complete RGB16 files verify at each gate. V50
separately retained ViT-S and tested data membership alone. The subsequent
[paired-data-only trial](paired-expansion-v53-v54-4k-review.md) completes both
original 4,000-step schedules without sustaining its early photographic gain.
The reviewed corpus remains opt-in.

## Texture retention and training scale follow-up

[Achddou, Gousseau and Ladjal (2024)](https://arxiv.org/html/2404.07212v1)
study mixed natural/synthetic training and texture-acutance supervision for
RGB and RAW denoising. Their analysis motivates checking recovered texture
separately from noise power; aggregate acutance can hide frequency overboost.
This older methodological work is context, not a recent architecture or a
reproduced result here. The new exact sinusoid diagnostic fits signed carrier
response, quadrature leakage and unrelated residual energy separately.

The [AIM2025 real-world RAW denoising report](https://arxiv.org/html/2510.06601v1)
describes substantial attention to data/noise synthesis and progressive patch
sizes among entrants. Our256px training/512px serving geometry warrants a
future controlled context check; the report does not prove this project's
detail loss comes from patch size. Its RAW-to-RAW benchmarks, additional data
and compute budgets differ from our commercially usable joint reconstruction.

[Experimental weak-texture source and actual CPU preparation](weak-texture-source.md)
remain default-off after the [negative/mixed V55 first gate](weak-texture-v55-review.md).
Any further change needs matched trained quality, flat-region false-detail
checks and the standing full/native/GFX review.

## Learned input adaptation candidate

Re-reading the [August 2026 structural-guidance method](https://arxiv.org/html/2608.09995v1#S3.SS3)
confirms that it adapts frozen DINOv3 patch features after encoding a fixed
sparse pseudo-RGB input. It does not evaluate the learned RGB input adapter
implemented here. Our [optional input-adaptation experiment](dino-input-adaptation.md)
instead adds a local residual before the encoder, preserving its initial input
exactly and differentiating through frozen pretrained weights. The motivation
is the measured noisy-preview feature gap and negative current-branch ablation,
not a claimed reproduction or an inference that feature similarity guarantees
restoration quality. Actual parent-weight identity/gradient/portability checks
and the 483-test CUDA-enabled suite pass. The [matched first gate](dino-input-v56-review.md)
then loses natural-photo and known-camera means, with no clear native detail
advantage. The option stays default-off. One seed/1,000 updates is not convergence
or a universal rejection of input adaptation. A same-source control replay is
now complete in the [unchanged-control replay](control-replay-v57-review.md).
The original fresh schedules now have a [complete 10,000-update review](fresh-dino-capacity-10k-review.md).

## Centered RAW reconstruction candidate

The independent [centered-RAW reconstruction prototype](raw-kernel-reconstruction.md)
now constrains the output head to preserve clean constant camera RGB rather than
adding another color-mean loss. It conditions sample-difference coefficients on
the existing DINOv3/RGB features. Actual legacy/default-off CPU predictions match
exactly, and genuine-parent CPU restart/gradient checks pass. It remains
default-off: noisy-field unbiasedness, CUDA behavior, trained detail and speed
have not been established. It is not an implementation or quality reproduction
of the 2026 continuous-kernel method referenced in that note.

## Recent RAW denoising comparator

[Sánchez-Beeckman and Buades (April 2026)](https://arxiv.org/abs/2604.17453)
study learned nonlocal feature matching and filtering for RAW-to-RAW denoising.
The [official source and release](https://github.com/MIA-UIB/nonlocal-matchfilter)
now have a [genuine-weight CPU probe](nonlocal-matchfilter-cpu-probe.md) here:
strict upstream tensor matching, actual native CPU sampling and two fixed
photographic observations followed by independent Malvar. Fine cords and cloud
detail remain soft. This is a small cascade comparison, with different training
data and budget; no full-suite, real-camera, CUDA, SOTA or speed result follows.
The [optional evaluator and standing GFX contexts](nonlocal-reference-integration.md)
pass genuine CPU replay and native review. The [completed CUDA/full-suite
comparison](nonlocal-reference-full-review.md) now includes genuine native
operators, full427/paired panels, full102MP GFX output and three cameras. Its
synthetic-photo scores are lower; small paired-real differences are uncertain.
The reference remains optional and establishes neither SOTA nor broad real
superiority for this project.

## DINOv3 convolutional feature pyramid

The [official ConvNeXt-Tiny model](https://huggingface.co/facebook/dinov3-convnext-tiny-pretrain-lvd1689m)
is accessible at pinned revision `10d30274b4d445111e2d5bf75ac93bbd94db274b`.
Its genuine pretrained weights match their Hub LFS SHA256 and use the existing
DINOv3 license. Official Transformers code and our rectangular CPU probe expose
four spatial feature maps at 1/4, 1/8, 1/16 and 1/32 input resolution. That motivates
an [optional top-down fusion branch](dino-convnext-pyramid.md) at three CNN
resolutions, rather than claiming that a denser feature grid guarantees more
faithful image detail. Backbone and fusion capacity change together. Genuine
CPU engineering and a four-update actual-trainer complete-state restart pass,
including Commons/native/paired domains. Genuine CUDA preflight and the complete
496-test CUDA suite pass. Its [first1000 trained review](dino-convnext-pyramid-v58-1k-review.md)
includes120 inspected native comparisons and full GFX/three-camera evidence,
without a clear overall winner. The original10k schedule has a
[completed mature review](dino-convnext-pyramid-v58-10k-review.md): the photo
mean ties the fresh no-context model, with persistent color/detail limitations.
The [matched wider-palette trial](wide-flat-palette.md) is an intervention under
review, not a promotion.

## October 17 follow-up: recent reconstruction and noise methods

The [RawForge publisher registry](https://github.com/rymuelle/RawForge/blob/79f17700c29765b28a4cf5bd1b6d90bc7e3eb7f2/RawForge/application/MODEL_REGISTRY.py)
offers blind six-channel joint models with registered256/768px serving tiles.
The [new CPU comparison](rawforge-cpu-pilot.md) verifies publisher signatures and
all tensors, explicitly ports one CUDA device constant, and reviews fixed
photo/GFX crops. The [completed original-export GPU follow-up](rawforge-original-gpu-review.md)
passes its fixed no-autocast CPU comparison bound and reviews all 24 native
triplets; no model is promoted from those six selected observations.
Training geometry/membership and separate weight-license terms are unverified;
no new default or SOTA claim follows.

[Biscarrat et al., CVPR Findings2026](https://people.csail.mit.edu/cjbisc/burst/burst_paper.pdf)
predict continuous reconstruction weights from sample offsets, color identity
and encoded local information. This is relevant to sample-preserving RAW
reconstruction, but its burst/aberration setup is different. Equation1 permits
signed cross-color weights and divides by their absolute sum. Our inference:
that formula does not by itself guarantee preservation of every constant RGB
color. A constrained filtering variant would be a new experiment, not a
reproduction or an established fix for our learned color shifts. No code or
weights from this paper are incorporated.

[Lu et al., 2-Shots in the Dark](https://arxiv.org/abs/2512.03245)
use one noisy image and one dark frame per ISO to synthesize shot noise and
signal-independent noise with spectral/histogram constraints. This motivates
checking real sensor correlations; it does not supply a calibration for our
GFX captures. No fabricated camera-specific dark-noise model is added.

The [official darktable5.6 release](https://www.darktable.org/2026/06/darktable-5.6.0-released/)
names RawNIND UtNet2 as its default RAW AI model, already covered by our existing
reference. That integration is not a separate independent restoration method.

The [July2026 GALOSH paper](https://arxiv.org/abs/2607.03768) separates local
Walsh–Hadamard luminance shrinkage from guided chroma filtering. Its
[Apache-2.0 publisher implementation](https://github.com/luxgrain/GALOSH)
has a [completed small CPU-port comparison](galosh-cpu-pilot.md) here. Two unused
SSE helpers/headers need AArch64 guards; canonical processing remains unchanged,
without original x86/GPU parity. A two-thread exact repeat fails by small floating
differences; the separately rerun serial probe passes its repeat and full array/
metric/native checks. Native crops lose cords/fence contrast despite noise
removal, so no full benchmark, quality upgrade or GPU-speed claim follows.

## Noise-fit support follow-up

[RPG-VST, July 2026](https://arxiv.org/abs/2607.24291) motivates checking robust
single-image noise fitting and stabilized variance reliability. The new
[current-estimator stress study](noise-calibration-fit-support.md) finds accurate
tested in-range variance but significant deep-shadow extrapolation in some
synthetic cases. This is our own known-noise diagnostic, without an RPG-VST
implementation, camera calibration or changed conditioning. The standing GFX
foliage context contains observed phase-patch means below its fit's support;
that is descriptive, without real variance truth or a claimed cause of detail loss.

The structural-guidance paper's stated public
[repository](https://github.com/Calista-pedi/SG-for-JDD) was checked again on
2026-10-17 at08:34UTC; GitHub's repository API returns404. This records public
availability at that time and does not establish that no private/supplementary
code exists. The active model experiment continues independently.

## vkdt compact JDD reference and CPU precision

The [publisher's JDD module](https://github.com/hanatos/vkdt/blob/ec070207e8fb22cc9d01cb7293ce382ef06c53c1/src/pipe/modules/jddcnn/readme.md)
deploys an OIDN-derived compact Bayer/X-Trans U-Net through a2026 Vulkan
compiler/scheduler. Its [genuine noisy-Bayer ONNX CPU probe](vkdt-jddcnn-native-CPU-probe.md)
strictly matches all42 learned tensors and reviews eight fixed native contexts.
Selected flat colors are closer than our control20k, but photo/detail results
are mixed. An exact-weight FP32 graph agrees with the upstream operator while
native CPU FP16 execution differs materially; no Vulkan quality/speed or general
model ranking follows. The older compact architecture is not a new2026 design.
Weights/runtime stay isolated; separate weight-license terms remain unverified.

## October 19: noise assumptions before another architecture change

The [AIM 2025 RAW-denoising report](https://arxiv.org/html/2510.06601v1) attributes
important gains to synthesis/training strategies and provides real dark-frame
profiling material. Its RAW-to-RAW/ISP protocol differs from our joint task.
Our inference: check residual-noise assumptions before introducing another
camera-specific augmentation. The new [cached GFX correlation diagnostic](gfx-noise-correlation.md)
finds no clear sky departure from its conditional independent-noise simulations
at the tested Haar offsets. Textured contexts remain structure-confounded.
Known row/column controls and an independent numerical audit pass. This is a
limited input-only diagnostic, without noise-truth, quality or calibration claims;
no upstream data/code/weights or noise-model changes follow.

## Mature FP32 execution candidate

The current [Triton dot API](https://triton-lang.org/main/python-api/generated/triton.language.dot.html)
supports a three-product Tensor Core precision mode. Its
[pinned3.8 compiler pass](https://raw.githubusercontent.com/triton-lang/triton/v3.8.0/lib/Dialect/TritonGPU/Transforms/F32DotTC.cpp)
motivates an inference-only hidden-convolution candidate. The
[genuine mature-model CPU proxy and offline SM121 compilation](mature-tf32x3-convolution.md)
find small tested output differences and compiler acceptance. CPU arithmetic
is not Tensor Core parity. The [completed actual CUDA follow-up](mature-tf32x3-cuda-review.md)
passes all six numerical cases, with maximum 0.06640524 DN16 difference, but
resident medians are 8.9–10.1% slower. No production code path, learned weights or
training recipe changes follow. This is execution research, without a new
architecture or quality claim.

## Matched input context after the original20k data review

The [completed native-data comparison](native-data-original20k-review.md) finds
no positive matched photographic effect from the 22 extra native captures and
no clear native detail gain. The AIM 2025 progressive-size results cited above
motivate the separate [fixed input-context trial](training-context-v86-v87.md).
Our inference was to isolate surrounding input pixels from the number of clean
supervised pixels; the paper does not identify our failure's cause. Both arms
use the same320px source/noise draws and256px loss region, with256px versus320px
model forwards. The [completed original4k review](training-context-original4k-review.md)
finds +.00099dB matched photo PSNR with an interval crossing zero, failed
known-camera/weak-detail gates and no clear native detail gain. All125 native
cells are viewed; no model is promoted or extended. This is an independent
controlled test rather than a reproduced progressive-size method.

The [June 2026 MambaRaw paper](https://arxiv.org/abs/2606.24479) instead studies
JPEG-conditioned reconstruction with stored metadata for coding. Its task
differs from noisy-Bayer restoration, so its reported efficiency is not evidence
for replacing this project's denoiser.

## Physics-conditioned pretrained reference

The [RAM authors' implementation](https://github.com/matthieutrs/ram/tree/0de1617403291e5a28179097795752200e65b82c)
adds multiscale forward-operator conditioning to a DRUNet-style reconstruction
network, with Poisson/Gaussian noise inputs. The
[completed zero-shot CPU pilot](ram-CPU-pilot.md) strictly loads all825 published
state tensors and checks four Bayer phases before six fixed photo/GFX cases.
Both photographic PSNR/SSIM scores trail retained V43/V63. More real-scene
texture accompanies residual grain and fine sky patterns; no broad native gain
is established. All30 native board cells and12 independent PSNR replays verify.
The model stays an isolated reference, with no adaptation on qualitative captures,
production dependency, DINO replacement, full-frame continuation or promotion.

## Wavelet-guided RAW reference

The [July 2026 WGCAN paper](https://doi.org/10.1016/j.imavis.2026.106137) and
[pinned authors' code](https://github.com/user-hbj/WGCAN/tree/87413dd280af8228f34fe33188136077ad81ca68)
provide wavelet-guided RAW restoration and a learned RGB ISP. The
[completed RAW-stage/Malvar CPU transfer pilot](wgcan-RAW-CPU-pilot.md) loads all
294 released state tensors and checks all four Bayer layouts before six fixed
photo/GFX cases. Its photographic scores trail retained V43/V63; native crops
show periodic grids and lost fence structure. All54 triplet panels, 30 board
cells and12 PSNR replays verify. This evaluates our composition with an
independent demosaicer, not the full published RGB pipeline or paper scores.
Unverified upstream license terms keep source/weights in an isolated research
cache. No production dependency, training change, broad ranking or promotion
follows.

## Coherent frequency evidence after the context comparison

[FFNet, April2026](https://doi.org/10.3390/math14071175) combines global and
local Fourier feature blocks with channel attention for joint demosaicing and
denoising. That primary paper motivates checking frequency evidence, without
establishing a remedy for our physical shot-noise/detail failures. The new
[fixed V88/V89 experiment](spectral-v88-v89.md) instead uses a shared input-RAW
noise-normalized spectral mask and a zero-initialized scalar residual gate around
the existing frozen-DINO-guided mature model. This is our independent design,
not an FFNet reproduction or transfer of its Gaussian-noise benchmark results.
No upstream code or weights are incorporated. Numerical/gradient correctness,
flat false-detail controls and matched trained photographic/native quality are
separate requirements; an analytic Gaussian bound is not calibrated for our
Poisson/ADC noise or input-derived variance proxies.
