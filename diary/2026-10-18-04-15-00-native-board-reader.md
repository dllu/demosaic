# Prepare native crop review boards while the matched DINO run continues

Previous goal turns were verified45s waits on exact DINO child
2884352/1792313905.76. It advanced through6k/8k with producer archive receipts;
the next decision remains the completed10k/160k-example numerical/native review.
No training restart, recipe change, new data admission, new GPU job or automatic
extension. The worktree was clean at63612ce before this engineering change.

Inspected the old native board helpers. They hard-code new2k / original RAW8k
labels and some fixed checkpoint digests; reusing them unchanged for10k/old40k
would mislabel the evidence. Added scripts/build_native_crop_board.py: one saved-
PNG reader with explicit report kind and labels/checkpoint hashes taken from the
report. Complete optional aliases preserve the original labels. It handles seven
existing report schemas, retains each crop's provenance, validates shared metadata
and exact noisy/reference panels, and copies native160px cells without resizing
or color conversion. Real references and model comparators remain labeled as such.

All18 focused tests pass (0.38s), including wrong hashes, resized/out-of-bounds/
overlapping panels, reference/noisy labels, noise/ROI/exposure mismatch, missing
metadata, changed checkpoint, duplicate/missing cells, changed outer pixels,
ambiguous aliases and overwrite rejection. Both source/test Ruff checks pass.

Executed a frozen-source CPU replay on completed first32k reports, not the pending
10k outputs: known+unseen, full427 photos, analytic, full GFX, three-camera, hue
and highlight contexts.130 triplets,178 unique native board cells,390 original
panel blocks independently compared on readback;138 report/PNG files unchanged.
Torch is never imported; no model forward, scoring, training or GPU work. Current
and frozen reader SHAe7e53952058c7c6e0624dcb117d39ce7a4ae184cef4561db3e64c89de80005cd.
The exact public result copy SHA
ff87992fb7f2fce719dfb7612d7c3ce2eb829349f55355eecf7fa09a0db59f0e.
Private evidence: /mnt/external/demosaic/benchmarks/native-review-board-reader-CPU-v2/.

The first replay completed the camera board then rejected synthetic RawNIND's
recorded weight_sha256 field (it uses that name instead of sha256). Preserve v1's
checker, reader, board and failure.json. v2 supports both explicit hash fields and
rejects conflicts; no PNG/hash/metadata tolerance changed. All seven formats pass.

Viewed photo and GFX replay boards with view_image/detail=original.52 native cells
checked for layout, full method labels and unchanged pixels; all labels fit. These
are old model outputs and this is an artifact/layout inspection, not a new quality
review or model result. No new performance claim, README change or promotion.

DINO was verified live before/after the replay and reached8,625 updates /
138,000 examples in the final observation.530.22GiB remains free. Finish the
original10k run and queued full review before choosing the next training budget.
