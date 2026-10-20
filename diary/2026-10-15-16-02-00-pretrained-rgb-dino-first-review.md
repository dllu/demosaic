# Pretrained RGB/DINO restoration and first 1k review

Previous goal turn was progress: expanded fixed Joint8 evaluation/native review
was completed and pushed; its full102MP GFX job was started. Verified that job
live rather than restarting it. It completed successfully: Joint8 967.31s,
V16 29.51s, RawNIND 15.99s, single shared-machine restoration timings excluding
decode/load/render/encoding. All six TIFF hashes, 8746×11662×3 uint16 geometry,
16-bit tags, three ICC sRGB profiles and >256 sampled code values verified.
Published native full-frame foliage/fence comparisons and receipt. More fence
structure survives blending, but soft foliage/color specks persist; no promotion.

Implemented an opt-in pretrained RGB restoration backbone with genuine frozen
DINOv3 context. DRUNet topology/tensor names adapted under both upstream MIT
notices, strict verified original RGB weight transfer; native CFA/mask/noise/
WB/matrix projection and DINO fusion start at zero. All restoration parameters
train, DINO stays frozen. IEEE FP32 physical features and first/last RGB and
measurement projections preserve weak native signal through BF16 training and
FP16 deep inference. This is affine-normalized linear RGB, not GAT/HQS. A
constant/unit and near-flat eight-sigma normalization floor was added before
GPU training to avoid amplifying clipped/quantized-flat noise inputs.

54,829,760 parameters, 33,233,216 trainable. Tests independently check original
weight inference, CFA geometry, per-image batch independence, native precision,
gradient flow, checkpoint roundtrip, and invalid configs. Genuine DINO CPU
training/resume and CUDA BF16 backward pass verified finite math, nonzero adapter
gradients, no frozen-backbone gradients. All226 tests passed18.08s; Ruff passes.
Built wheel inspected for exact final model/train source and all three upstream
license notices. Corrected the wheel-target name while adding license assets.

The first in-process GPU training attempt after evaluation stalled after step1
on data-worker queues: GPU0%, workers idle with one futex wait. Terminated only
that owned workflow and its eight child workers, preserved its diagnostic log
and initial checkpoint. Added opt-in spawned-worker configuration to all three
training loaders and verified deterministic CPU restart with spawn. Restarted
training through a fresh CLI, same initial snapshot and first-batch fingerprint.
No unrelated process stopped. That1000-step budget completed successfully.

V28: batch4, native256, LR1e-4, expected50% Commons/procedural,25% paired RAW,
25% binned native RAW synthetic; per-step data RNG and observation hashes.
Protected final and GFX/siblings excluded. Pretraining source/initial checkpoint,
actual runtime code, licenses, data manifests and all hashes archived.

First1k complete known4/unseen5 measured-CFA PSNR53.99180/53.62905, versus
V16 53.27465/53.07856 and RawNIND54.06860/53.56220. RawNIND delta−.07680/+.06685
has scene-bootstrap intervals including zero; AHD RGB39.06454/38.05576 and
SSIM.922445/.913260 still trail RawNIND. No overall quality win claimed.
Matched16-photo screen33.43530/.947856, versus V16 32.41824/.937421 and
initial30.59365/.904216; procedural31.76320/.961572. Photo gain+1.01706dB
overV16, bootstrap[+.74836,+1.32740]. Still below fixed Joint8 photo34.23888.
No full427 or protected-final evaluation yet. Native exact-GT triplets,
registered AHD real references and GFX comparisons published with source/ROI,
weight hashes, noise and display metadata. Foliage/fence improve overV16 but
remain soft/thick/irregular, with colored dots/texture. Fabric lines still lost.

`docs/pretrained-rgb-restoration.md` describes method/validation;
`docs/pretrained-rgb-v28-review.md` records this first review;
`docs/results/pretrained-rgb-v28-1k-review.json` is the full quantitative/crop
receipt. Frozen1k checkpoint2dd792004d55dbfabbace9b3f635444f39a6200a917837b052f59b83bed21d7b.

Next workflow is live: session86120, parentPID3832216, script
`.cache/full_v28_1k_then_resume.py`, log `.cache/full-v28-1k-then-resume.log`.
It first runs frozen1k full GFX output (childPID3832220, log
`.cache/gfx-pretrained-rgb-v28-1k-full.log`, output
`/mnt/external/demosaic/evaluation/gfx-3879-3880-pretrained-rgb-v28-1k-full/`),
then resumes the original schedule to5000 through a fresh spawned-worker CLI,
log `.cache/train-pretrained-rgb-v28-5k.log`. Full1k restoration already logged
24.88s versus V16 30.53s; final TIFF validation/native review still pending at
this diary observation. Verify authoritative processes before any restart.
The first1k paired/synthetic and GFX-context jobs all completed. Quality and
10-second speed objectives remain unmet. Existing V16 defaults unchanged.

Follow-up before commit: full1k run is terminal0; validated all six TIFF hashes,
geometry/16-bit/ICC/code diversity and all native PNGs, published
`docs/results/gfx-pretrained-rgb-v28-1k-full.json`. V28 24.87672s, V16 30.53070s,
RawNIND 17.42753s, same shared run. Full fence still thick/irregular, leaves soft.
Resume is now live PID3832886, parent3832216/session86120, passing2500. A
sequential review job PID3833838/session2125, `.cache/eval_pretrained_v28_5k.py`,
log `.cache/eval-pretrained-rgb-v28-5k.log`, waits on that exact training process
before complete known/unseen +16-photo +GFX-context evaluation. It never starts
training itself. Check these actual processes/outputs before any restart.
