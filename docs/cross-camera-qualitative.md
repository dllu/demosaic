# Cached Q2, Sony a7R II and GFX50R comparisons

Current comparisons include **V84 and its V100 continuation**, with V43 and
RawNIND as comparators. These extend the standing [GFX100S train scene](gfx-qualitative.md)
using three existing cached captures. V84/V100 look close here. The clearest
separation from RawNIND is on the GFX50R concrete; Q2 shadows and Sony windows
remain soft. These few low-ISO contexts do not establish a broad real-photo gain.

Each cell is an unchanged **160×160 native sensor-pixel crop**. Rows are the
fixed upper-left/lower-right regions; columns are noisy Malvar, V43, V84,
V100 and input-only CFA-channel-calibrated RawNIND. There is **no clean reference**.
RawNIND is a comparator, **not GT**, and no pixelwise quality score is reported.
Open the original PNG at 100% if the browser fits the board to its window.

[All 18 source triplets and metadata](images/current-cameras/manifest.json) ·
[Execution, float-render verification and actual-viewing receipt](results/cross-camera-current-v1.json).

## Leica Q2: rocks and shadows

![Q2: noisy, V43, V84, V100 and RawNIND comparator; no GT](images/current-cameras/q2-comparison.png)

The methods suppress fine grain but leave soft dark rock structure. These
crops do not show a clear overall V84/V100 advantage over V43 or RawNIND.

## Sony a7R II: airplane fuselage

![Sony a7R II: noisy, V43, V84, V100 and RawNIND comparator; no GT](images/current-cameras/a7rii-comparison.png)

All methods remove fuselage grain. Windows, joints and highlights remain soft;
V84 and V100 differ little at native size. The input itself is soft, so its
limited detail is not solely a restoration failure.

## GFX50R: concrete architecture

![GFX50R: noisy, V43, V84, V100 and RawNIND comparator; no GT](images/current-cameras/gfx50r-comparison.png)

The learned outputs retain finer concrete-surface variation and more coherent
joints than RawNIND here. V84/V100 look close to each other and V43. Without a
clean reference, not every retained fluctuation can be established as true
surface detail. The [exact synthetic detail gallery](heldout-detail.md) provides
a complementary check with known targets.

## Fixed inputs and display

| Camera | ISO | CFA | Shot estimate | Read variance | Display | Sensor context xywh |
| --- | ---: | --- | ---: | ---: | --- | --- |
| LEICA Q2 | 100 | GBRG | 4.3728329e-05 | 1.60487778e-07 | ×2 (+1EV) | [250,4054,512,512] |
| ILCE-7RM2 | 400 | RGGB | 8.19833844e-05 | 1.20619875e-07 | ×1 | [3984,2978,512,512] |
| GFX 50R | 100 | RGGB | 1.94142414e-05 | 1.64130628e-07 | ×2 (+1EV) | [1656,1552,512,512] |

Noise coefficients are the existing input-only Haar/flat-patch estimates,
not dedicated camera calibration. The [fixed selection](../configs/real-camera-qualitative.json)
records source SHA256s, noise profiles and regions. Native ROIs are
[64,64,160,160] and [256,256,160,160] inside each context. Even context origins
preserve CFA phase. Source coordinates are unrotated visible-sensor pixels.
These are 512-pixel context restorations, not full-frame results.

WB, camera matrix and display exposure are identical across methods. Sony uses
×1 to avoid clipping its white fuselage in the display; Q2/GFX50R use ×2.
No resizing, sharpening or method-specific exposure fitting is applied.
All inference is CPU FP32, with the standard loader selecting each checkpoint's
final EMA. Full hashes and effective configurations are in the manifest:

| Method | Selected endpoint | Checkpoint SHA256 prefix |
| --- | --- | --- |
| V43 | Original step2000 EMA | 0d74cf31fb1c |
| V84 | Original final20000 EMA | 134887e12357 |
| V100 | Fixed final10000 continuation EMA | 4b689fb187b1 |
| RawNIND | Publisher weights, observed-CFA channel gain | c1f7de3de24c |

All 30 distinct displayed cells were actually viewed at native resolution in
both the original review and published layouts. The 21 retained float32 context
arrays reproduce all 54 source-triplet panels byte-for-byte after display
rendering. Shared noisy and RawNIND panels match exactly across learned methods.
Source/checkpoint bytes stayed unchanged, and CUDA was not initialized.

The three cached RAWs total 218.7MiB in `.cache/real-camera-qualitative/`; only
these local copies were decoded. Originals remain read-only. Exact source
hashes/filenames are absent from the active Commons/native/paired training
manifests. These are existing development selections, with no complete
near-scene independence or strict-unseen claim. Photos by the project owner,
used with permission; public artifacts contain small crops and provenance.

## Reproduce

Source `scripts/env.sh`, then run the existing CPU comparison helper with the
fixed selection and desired checkpoints:

```bash
uv run --no-sync python scripts/compare_raw_crops.py \
  configs/real-camera-qualitative.json \
  /mnt/external/demosaic/models/v43-step2000.pt \
  /mnt/external/demosaic/models/v84-original20000.pt \
  /mnt/external/demosaic/v84-curated-quality-20261022-v2/train/V100/last.pt \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --rawnind-gain-modes cfa-channel --device cpu --precision float32 \
  --output /mnt/external/demosaic/current-three-camera-replay
```

The completed run used copied numerical source at
`.cache/current-quality-20261022-v1/three-camera-v1/work/`.
Its plan binds the cached inputs, weights and implementation. Outputs are in
`/mnt/external/demosaic/current-three-camera-20261022-v1/`.
The optional resized overview is separate from the native crops above.
The [earlier V43 execution receipt](results/cross-camera-v43-qualitative.json)
and timestamped diary preserve historical evidence.
