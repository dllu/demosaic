# Native crop review boards

[build_native_crop_board.py](../scripts/build_native_crop_board.py) rearranges
saved native160px triplets into review boards without inference, color conversion
or resizing. It reads method labels and recorded checkpoint hashes from the
reports. Optional display aliases must map every method uniquely; receipts retain
both names. This avoids carrying earlier step counts into a later review.

For example, after the matched quarter reports have completed:

```bash
source scripts/env.sh
uv run --no-sync python -P scripts/build_native_crop_board.py \
  /mnt/external/demosaic/evaluation/packed-isotropic-mixed16-quarter-known-v1/summary.json \
  /mnt/external/demosaic/evaluation/packed-isotropic-mixed16-quarter-unseen-v1/summary.json \
  --kind camera \
  --output /mnt/external/demosaic/benchmarks/mixed16-quarter-native-review-v1/cameras.png
```

Other explicit kinds are `synthetic`, `analytic`, `gfx`, `three-camera`, `hue`
and `highlights`. Select the kind matching the source report. Camera AHD,
separate ISO100 GFX and same-capture RawNIND comparators stay accurately labeled.
Use a new output path: existing PNGs and adjacent JSON receipts are preserved.

The reader requires a complete method-by-case rectangle, recorded checkpoint
hashes, matching shared source/ROI/noise/display/reference metadata, verified
source PNG hashes, in-bounds nonoverlapping160px panels and identical noisy/
reference pixels across methods. All saved board cells pass exact readback.
The receipt retains original triplet metadata and pixel/source coordinates.
Checkpoint hashes are retained from reports; this utility does not reopen the
weights or establish the correctness of the original rendering or model results.

The [CPU replay](results/native-review-board-reader-CPU-v2.json) passed all seven
formats using completed first32k reports:130 triplets,178 unique board cells and
390 original panel blocks checked against the boards. All138 source files remain
unchanged. It imports no model package or Torch.18 focused tests include mismatch,
missing-method, wrong-reference-label, pixel/hash, alias and overwrite rejection.
The photo and GFX replay layouts were also inspected at native size. An initial
replay rejected RawNIND's `weight_sha256` schema; support now retains that recorded
field with unchanged hash equality. Its first checker/source/failure remain saved
privately. No new inference, score or quality finding was produced.

The [selected-color audit adapter replay](results/native-selected-color-bridge-CPU-v1.json)
also passes:16 earlier triplets,24 native cells and48 original panel blocks.
Those records use the existing `hue` analytic schema. A private adapter wraps
the audit's `additional_native_crops` collection and copies its eight PNGs into
the review cache; original metadata/pixels and all18 source files are unchanged.
The board reader and frozen workers are unchanged. This prepares the selected
neutral/fabric/cyclic-palette inspection without repeating inference.

Boards supplement the original noisy/denoised/GT triplets. Continue embedding at
least two original native triplets in model performance reports, with their
source/ROI, checkpoint hash, noise conditioning and display exposure. Manual
inspection and the actual matched quality decision remain required. The queued
review and frozen production workers are unchanged.
