# V113: train the larger encoder with fitted feature transfer

**V113 is queued for a CUDA check and a fresh 20,000-update quality run.**
It uses the fitted Small initializer, preserving V104's learned fusion gates.
The completed V111 Tiny continuation supplies the trained control. Eight
discarded CPU optimizer updates pass; CUDA and production have not started.

[Actual CPU evidence, source hashes, recipe and live queue](results/small-aligned-training-queued-v1.json) ·
[Production recipe](../configs/quality-v104-small-aligned-v113.yaml).

The question is whether a larger frozen DINOv3 encoder, transferred without
the blind swap's color artifacts, improves restoration after joint training.
This measures Small **plus fitted transfer**; it does not isolate capacity
alone. The earlier zero-gate Tiny/Small preparations remain preserved and
unlaunched, answering a different initialization question.

## Initializer and control

The [training-only feature fit](small-feature-transfer.md) maps four Small
feature stages to V104's learned Tiny lateral outputs. Its fixed 64-source fit
uses training images only; sixteen separate training images check transfer.
The fit changes eight lateral weight/bias tensors and preserves the other
83 EMA tensors, including all three nonzero learned gates. The frozen official
Small revision and numerical weight identity are verified.

The initializer is
`/mnt/external/demosaic/Small-lateral-alignment-CPU-20261024-v1/Small-aligned-from-V104.pt`,
SHA256 `6a055cb6f5e03676c69a9523350e9236b7e19f162b6ca9f535858d14d42e8baa`.
Its inherited step20000 describes V104 history: it has **zero new joint updates**.
The selected transfer observations nearly preserve Tiny's photo means, but
the two adverse-camera scores remain .25–.26dB below Tiny. High-noise fine detail
is still soft. [Existing native triplets and GFX comparisons](small-feature-transfer.md#fixed-material-and-camera-observations).

V113 follows V111's completed continuation recipe from that same V104 history:

| Setting | V113 Small | Completed V111 Tiny control |
| --- | --- | --- |
| New joint updates | 20,000 planned | 20,000 completed |
| Seed / optimizer / EMA | 62 / fresh AdamW / fresh EMA | Same |
| Batch / patch / precision | 16 / native256 / BF16 | Same |
| LR / warmup | 1e-5 / 200 updates | Same |
| Reconstruction epsilon | .001 | .001 |
| Cleaned Commons sources | 90,864 | Same |
| Geometry / optical blur | 4× → geometry → area2 / zero PSF | Same |
| Fine-detail sampling | Six reviewed ROIs, 5% conditional-photo; weak textures and photographic contrast attenuation | Same |
| Native / paired RAW targets | 128 / 32 | Same |

The architecture/feature basis and fitted lateral initialization differ.
All other recipe values match apart from run paths and explanatory metadata.
There is no duplicate Tiny production run. Original V104, completed V111 and
the fitted zero-joint-update initializer remain distinct references.

## Actual optimizer check

The frozen CPU recipe completed eight genuine forward/backward/AdamW/EMA updates
at native64/B1/FP32 on the original 20k LR schedule. This reduced-size check is
discarded and is not a quality or timing measurement.

- Exactly eight restoration forwards, eight Small-encoder forwards and eight
  optimizer steps; no CUDA or held-out quality inference.
- All 91 initial EMA tensors match the fitted checkpoint exactly; the 83
  inherited tensors and all three learned gates match original V104.
- All eight actual input fingerprints, domains, steps and learning rates match
  V111's earlier CPU check, including Commons/synthetic, native and paired RAW.
- The frozen encoder retains its official identity and receives no gradients.
  Model/EMA/Adam tensors stay finite; all 89 fresh Adam states finish at step8.

All frozen Python sources match the prepared production source. Its training
source hash was also reconstructed without model inference and matches the
actual CPU archive exactly. The numerical training/model/data/loss modules
remain identical to V111; intervening source changes concern optional evaluation
and inference behavior. The planned GPU check uses actual native256/B16/BF16.

## Queued execution and remaining measurements

The live controller waits for the exact existing GPU evaluation/export chain
and its independent audit to release CUDA. It reuses the successful CPU check,
then performs eight discarded CUDA updates. Only a successful CUDA check starts
the fresh 20k run from the original fitted initializer, with fresh AdamW/EMA.
The CUDA-check weights never initialize production. Failures and partial work
are preserved without automatic retries or resumes.

The worker counts actual training/validation/encoder forwards and optimizer
steps. It compares the eight CUDA and 801 production logged observations with
the original Tiny controls. Production's first actual outputs and loss must
also reproduce its own discarded CUDA check exactly. Unlogged production
inputs are not claimed to be independently verified.

Full 427-photo, known/unseen-camera, weak-texture, flat-color, standing GFX and
highlight comparisons remain required to assess the result, together with
native crop triplets and full 102MP RGB16 exports. DSCF3879/DSCF3880 remain
outside training; ISO100 is a separately captured qualitative reference.
There is no trained Small quality result yet, and the version plot gains no
new endpoint from preparation or discarded updates.
