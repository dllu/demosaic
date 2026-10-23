# V104 cached camera refresh and ADC projection diagnosis

Recorded: 2026-10-23T16:43:24-07:00 (America/Los_Angeles).

V104 remains the positive-noise/training baseline. Refreshed the standing Q2,
a7R II and GFX50R gallery with original V104 final20000 EMA on the same six
native160 regions. Three CPU FP32 DINO-backed forwards reused the original
input tensors: sampling the retained Bilinear RGB at measured CFA sites
reproduces the old five-input fingerprints exactly. The 91 EMA tensors and
frozen official Tiny hash were verified; weights/configuration/parameter IDs,
inputs and Torch RNG stayed unchanged. Twelve old float contexts and six V102
PNG triplets are byte-identical. All 15 contexts reproduce all 36 panels after
display; all 24 published board cells were viewed natively. No RAW decoding,
original source reads, new training admission or GT/scoring claims. Source hash
and filename absence checked in seven historical/current training manifests.

V104/V102 look close across these low-ISO regions. GFX50R concrete is more
coherent than RawNIND, while Q2 dark texture and Sony window edges remain soft.
Current README/model/docs now show V104 rather than leaving that gallery
frozen at V102/V103. Earlier galleries and machine receipts remain preserved.
[Completed camera execution and native review](../docs/results/cross-camera-v104-current-v1.json).

Investigated the V104 ADC yellow outlier using saved float predictions only.
Existing Malvar residual projection reduces the worst grid maximum absolute
channel-mean bias from 1218.0574 to 31.9088 DN16; the original yellow case falls
to 16.4466 DN16. Mean grid bias falls 14.4558 to 2.5652 DN16. Sites-only still
leaves 610.6677 DN16 in the tail. Of 588 ADC observations, V104 Malvar RGB MSE
improves in 531 and worsens in 57; the largest RMSE regression is .3691 DN16.
V102 and both untuned operators are reported on the same observations. This
repairs an analytic flat-color problem, not an established photographic gain.

Rehashed 1764 input/prediction bindings. All 3528 case/method metrics were
independently recomputed in Torch64 against NumPy64; 12 source triplets render
exactly in all 36 panels. Viewed all 16 board cells natively. Both crop cases
are explicitly post-hoc original worst-bias selections, with identical noise,
ROI and display and exact analytic GT. No target fitting or new neural forward.
[Diagnostic report and two native triplets](../docs/v104-adc-color-projection.md) ·
[Immutable audit and actual-viewing evidence](../docs/results/v104-adc-color-projection-diagnostic-v1.json).

Started a separate full427/four-CFA CPU FP32 photographic comparison of V104
original/Malvar/sites, one actual prediction per observation shared across
policies. Batch2, two threads, fixed 20k EMA and original seed42 validation
inputs. Planned 856 batched forwards/5124 score rows. First four forwards and
24 real score rows completed and were snapshotted; full results, independent
statistics and native review remain pending. No automatic export/promotion.
[Actual launch and frozen plan](../docs/results/v104-adc-photo-comparison-started-v1.json).

V111 was healthy at logged step3550 during that launch; V112 and the original
evaluation/full-frame/material queues remain waiting on their declared owners.
Their plans and original V102/V104 checkpoint bytes remain unchanged. This
CPU diagnostic does not change training or the current selector.

Two implementation mistakes were caught and preserved rather than rewriting
executed evidence: the initial camera worker omitted explicit shot/read and
failed before its first successful forward; corrected v2 uses the original
priors. The first flat diagnostic attempted to write outside the copied
implementation's permitted worktree and failed before producing a report;
corrected v2 uses a new /mnt/external output. Neither failed output was selected.
Their source/log/partial artifacts remain referenced in the completed receipts.

Verification before committing: seven existing mixed-profile/positive-prior
projection tests passed in 3.14s (15 deselected). The documentation/receipt pass
verified 64 reference occurrences/35 unique file hashes, all 24 new public
triplets, 140 local Markdown links/fragments across eight files, seven frozen
plans and seven live PID+creation handles. The current selector and all existing
machine receipts remain unchanged. Private verification receipt:
`.cache/current-quality-20261023-v1/V104-camera-and-ADC-review-v1/verification.json`.

Rechecked the requested `feat/linear-dng-export` integration: remote and local
tip are `4381fc23b6e4dc6245d201abb0d6e929dae38f14`, already an ancestor of HEAD.
Hot-pixel/linear-DNG support is merged; no further merge was needed. Its prior
focused validation remains documented in the earlier integration work.
