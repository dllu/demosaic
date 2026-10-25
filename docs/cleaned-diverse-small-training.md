# V119: cleaned Commons and more paired scenes on the Small model

V119 completed the full 20,000 updates from the final V115 Small EMA.
Both discarded implementation checks passed: 16 CPU updates at 64px/B1/FP32
and 16 CUDA updates at native 256px/B16/BF16. The production run started fresh
from V115, with fresh AdamW and EMA. Full quality evaluation is running; the existing
V114 general, V115 camera/detail and V117 photo-score options remain documented.
[Recipe](../configs/quality-v115-cleaned-diverse-v119.yaml) ·
[Started-run and queued-review receipts](results/v119-training-start-v1.json).
[Completed training, immutable endpoint and actual counts](results/v119-training-completed-v1.json).

All 20,000 model/optimizer updates and 640 scheduled validation forwards finished.
Actual domain counts match the declared 10,013/5,021/4,966 batches. The final
EMA checkpoint is immutable with SHA256
`b3c0d43264c6ad8446dd930aafa337298e4690d0d08f2967824f03ecd844f427`.
All 89 AdamW states reached step 20,000; model/EMA/optimizer tensors are finite
and the official Small encoder remains frozen. These are training-completion
checks, not a model-quality recommendation.

Small has the stronger known-camera mean and eight-pixel analytic response.
The [full saved-output natural-detail comparison](local-material-detail.md#tiny-versus-fitted-small-on-the-same-full-photo-support)
finds nearly unchanged faint natural-detail recovery versus Tiny. It is a useful
architectural parent for another data trial, with no claim that capacity alone
solves the remaining softness. Its fitted lateral layers are retained; this run
does not repeat the earlier feature fit.

## Data and training

| Setting | V119 |
| --- | --- |
| Parent | V115 Small, final 20k EMA |
| Commons | 90,791 cleaned training sources; original-source-preserving sampling reference |
| Paired RAW | 83 publisher IDs / 71 groups / 166 cases / 1,492 cached crops |
| Native clean RAW | Existing 128-ID corpus, unchanged |
| Domain probabilities | 50% Commons/procedural, 25% paired, 25% native |
| Paired camera probabilities | Sony 75%, Canon 6D 12.5%, Nikon Z6 9.375%, Nikon D40 3.125% |
| Training | Seed 65, 20,000 steps, B16, native 256px, BF16, deterministic execution |
| Optimizer | Fresh AdamW, LR 1e-5, 200-step warmup |
| Targets | 4× binning → geometry → area2; optical PSFs off |
| Weak detail | Legacy weak textures .15, fine-texture quota 0, photographic contrast attenuation .25, six reviewed ROIs .05 |
| Loss | Reconstruction epsilon .0003; paired epsilon .0001; band term off |

The [Commons cleanup and actual reader proof](results/cleaned90791-source-reader-preflight-v1.json)
exclude reviewed unsuitable targets while preserving unaffected source draws.
The [paired extension](paired-camera-sampling.md) retains all four corrected
legacy reference masks and every registered new case. Camera weighting avoids
raising Sony's share simply because it has most of the newly added groups.
Native and validation manifests retain their parent hashes. GFX3879/3880 and
protected scenes remain excluded from training; no source originals are changed.

The declared seed produces 10,013 Commons, 5,021 paired and 4,966 native batches.
Only the selected domain is loaded. Checkpoints and validation run every 1,000
updates; the full endpoint is reviewed after 20,000. This is a combined data
recipe plus additional training. It does not isolate the effect of corpus size,
reference masks, camera sampling or extra optimization individually.

## Completed training and quality review in progress

The seed first reaches native data at step 14, so both discarded checks cover
16 updates: 11 Commons, four paired and one native batch. Each verifies the
exact 91-tensor parent EMA, official frozen Small encoder, 89 fresh AdamW states
with the correct step count, finite model/EMA/optimizer tensors, all manifests
and the actual source archive. Production's first logged loss equals the CUDA
check's first loss. This establishes implementation behavior, not quality.

The original controller and input/source hashes are bound in the receipt.
It uses a 24GiB CUDA model quota, 48/24GiB start/runtime available-RAM floors,
128/96GiB internal disk headroom and 208GiB external input reserves. Jobs are
bounded; failures preserve their sources and evidence without automatic retry.

The queued endpoint evaluation runs eight FP32 stages: full photographic,
known/unseen camera, weak carriers, color, ordinary GFX, highlight GFX and the
complete 101.996MP GFX frame. It declares 4,586 model/encoder calls and 14,190
primary numerical observations for V119 alone. An independent CPU audit then
checks retained predictions and targets without new inference or noise.

Saved V115, V114 and V117 outputs are reused for three matched contrasts.
Each covers the full 427-photo support, all primary/analytic records and
5,124 photographic local-detail cases with the same 96,075 GT blocks. Reusing
blocks and controls across contrasts adds no independent sources. Two RGB16
exports receive exact native-region quantization checks at 460,800 channel values.

The review prepares at least two native 160px noisy/denoised/exact-GT triplets
and all six GFX regions, including foliage and chain-link fence. It retains
identical coordinates and display transforms without resizing pixels. GFX's
separate ISO100 exposure is an approximate reference, not GT. Actual viewing,
interpretation and current documentation updates follow the completed results.

The additional [DSCF3842/3835 fine green mesh](gfx-green-mesh.md#v119-after-cleaned-data-training)
has completed its endpoint review under both previously fixed noise profiles. It uses
the saved768px RAW context and all seven earlier nominal/nearby-profile control
predictions. Two new V119 CPU FP32 forwards add no fresh noise or RAW decoding.
That case supplements the original six main GFX regions; no independent ISO100
reference is exact GT.
At matched conditioning V119 shows no clear fine-lattice recovery gain over
V115. The larger numerical and main GFX results remain pending.

A supplementary [native-camera development comparison](native-camera-development.md)
is queued after that original job chain. It compares the final V119 checkpoint
with V114/V115/V117 and RawNIND on 240 new, shared stored observations from
11 held-out camera captures. Low-noise reference estimates retain their own
scope and do not replace the primary panels or real GFX review.

A byte-verified persistent copy of the completed endpoint is available at
`/mnt/external/demosaic/models/v119-final20000.pt`. Its availability does not
change the current model recommendation while full comparisons are running.
