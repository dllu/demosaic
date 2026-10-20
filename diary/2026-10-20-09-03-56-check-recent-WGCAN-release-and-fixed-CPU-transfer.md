# Check recent WGCAN release and a fixed CPU RAW-output transfer

The previous goal turn was progress: saved-array/native review was tested on
historical bytes and queued behind the fixed uniform-physics CUDA probe.
At entry the actual training/review/probe/CPU-review owners were live, the
global arm was2700 with124 recorded input/forward/loss hashes matching, and
all waiting controllers had no active children. The full PROMPT.md goal remains
active: SOTA/native superiority and100MP/10s are not established.

Reviewed existing research/negative experiments first, then searched primary
sources for recent joint RAW reconstruction. The July2026 WGCAN publisher page
links an available official implementation/checkpoint. Pinned repository commit
`87413dd280af8228f34fe33188136077ad81ca68`;29 text files and the46,852,051-byte
default best_raw_model.pth match their Git blob SHA1 identities. Checkpoint
SHA256 `61ca1440ade7e9230af46f4d90644e05255637048aac24152b0ab19fff24ed98`.
No license file/header was found in that pinned tree; GitHub's license field is
null. No publisher source/weights/data enter production or training.

The release's test program has a filename argument inconsistent with the
one-argument model forward, and its package initializer auto-imports unrelated
variants with broken absolute imports. The isolated CPU wrapper supplies only
a module namespace and calls the unchanged original CBAM/common/WCGAN_Two files.
All294 genuine state tensors strictly load and are finite; the original model
has11,681,731 parameters. Generated native64×96 RAW/RGB outputs are finite and
repeat exactly, with model/input/RNG/parameter IDs unchanged and no CUDA.
Compatibility receipt SHA256
`b0f687f187d3cca503d076e613e12de78b29261b42668177b59af14b7cf4e3f2`.

Prepared a fixed pilot before inference on the two existing256px noisy photos
and four standing512px GFX contexts. Its RGB target is LibRaw ISP output, not
our canonical camera-linear target, so use the declared RAW-output+MHC cascade.
Full original RAW/RGB forward still executes and both outputs are saved; only
RAW is used for comparison. Inputs clip0..1, exposure ratio stays1, RAW output
clips0..1 as in the publisher protocol, then ordinary Malvar runs before common
WB/matrix rendering. The checkpoint is blind and receives no shot/read prior.
There is no target/exposure/noise fit. Calibration/pretraining/task/device
differences prevent architecture attribution or reproduced publisher RGB claims.

The pilot completes entirely on CPU FP32/two threads, preserving state and RNG
and verifying exact repeats. V43 uses previously saved genuine FP32 GPU arrays,
with exactly the same observations. No new V43 forward/noise/training/GPU occurs.
All12 triplets/24 native160 cells are actually viewed at original resolution
before scoring. WGCAN RAW+MHC still omits canopy cords and adds stronger
periodic building/fence patterns; foliage looks crisper with more patterned
residual. ISO100 is a separate qualitative reference, never scored as GT.

After views, standard native240/border8 sRGB PSNR/SSIM:

- Canopy: V4340.6908/.969061; WGCAN RAW+MHC29.1423/.886486.
- Building: V4335.2076/.968224; WGCAN RAW+MHC24.3635/.737269.

Both native160 scores are also retained. Independent FP64/fsum PSNR agrees
within.00000154dB over all eight values. Independent NumPy MHC stencils replay
all3,538,944 camera-RGB output values within1.49e-7, preserving every measured
CFA phase exactly. These are small fixed-transfer observations, not broad
architecture/RawNIND/SOTA conclusions. No full-suite/GPU continuation is selected.

Artifacts: `.cache/research/wgcan-20261020-v1/`, with original API/source/blob
receipts, unchanged checkpoint, owned executed CPU drivers, full prediction
arrays, plans, native review, descriptive scores and independent physical audit.
Published `docs/wgcan-raw-mhc-cpu-pilot.md`, two native synthetic-GT triplets and
both full native boards, with source/ROI/checkpoint/noise/display/license records.
Registry SHA256
`7bd27852c698c940e6556b31edc50e22e4a26bb64306061c501be2dd3e01c4be`.
Updated the research index outside all active frozen source/input bindings.
No new production code/test is needed for this documentation/reference artifact.

Final actual check: global V90 at3250 with146 recorded hashes matching; training
and all deferred review/probe owners remain live, their waiting children absent.
Available RAM58.0GiB, system110.1GiB/external517.7GiB free. Original personal
RAFs/source drives remain untouched. Main quality trial, final native review
and the actual batching CUDA result remain outstanding; no model/default changed.
