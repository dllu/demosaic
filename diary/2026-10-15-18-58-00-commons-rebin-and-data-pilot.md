# Reuse the 4× base and review the first expanded-data pilot

Recorded 2026-10-15 18:58 PDT / 2026-10-16 01:58 UTC.
Previous goal turn classified as progress: commit a50754d prepared the first
audited Commons extension and published complete V32/V33 first1k reviews.
The overall PROMPT quality/speed objective remains active and unmet.

V33's resumed step2000 review completed and stopped. Checkpoint SHA256
`847ddfd8358bc8b1a793348753791667d71fb7265c64d04eec9029baa17a006d`.
Known/unseen measured-CFA means are 54.21306/53.72039, auxiliary AHD RGB PSNR
40.01869/38.42326, SSIM .931727/.919000. Against its first1k, unseen primary gains
.08887 dB (95% scene interval [+.02405,+.15704]), but known primary loses .05617
and the 16-photo synthetic screen loses .09558. Mixed tradeoffs do not justify
promotion. Published a complete numerical receipt, two exact synthetic GT native
triplets, paired samples and all four GFX regions. Fine texture/foliage/mesh
deficits and a colored point remain. These GFX crops use512px context; no new
full427 or full102MP claim is made for this checkpoint.

Started V35 from the same V30 EMA as V32, with fresh AdamW/EMA, seed46, batch16,
LR3e-5/planned3000, original8× processing and25% paired/25% native/50% Commons.
Only Commons training membership expands40170→41978. Runtime code, initializer,
validation and native/paired manifests match V32. All27 logged paired/native
observation-target hashes match across41 logged steps. Commons assignments
change with the source count; this is a single-seed corpus pilot.

V35 first1000 checkpoint SHA256:
`09a491b65e618e5b33819717f57bf54f8b7dd520ce3108b8c888caeb71d65741`.
Known/unseen primary means54.25055/53.80858, auxiliary RGB39.89707/38.36566 and
SSIM.930343/.919357. Unseen primary gains .04306dB versus V32 (95% scene interval
[+.00727,+.07886]); its mean exceeds channel-calibrated RawNIND, but auxiliary
RGB/SSIM still trail that comparator. The16-photo screen loses .06106dB
([−.12505,−.00066]) with almost unchanged SSIM. Native GFX review shows no decisive
visual gain. Published the complete first1k receipt and ten native triplets,
including two noisy/restored/exact synthetic GT examples. Both source credits,
licenses, ROI/noise/display and checkpoint/source hashes are recorded. No resize;
real AHD/ISO100 remain references, not exact RGB GT.

V32 and V35 now continue sequentially to step2000 using their original schedules,
with shared logged non-Commons draws checked before another matched development
review. Detached workflow PID232246 and log
`.cache/continue-review-v32-v35-2k.log`; status receipt
`/mnt/external/demosaic/runs/corpus-v32-v35-2k-workflow.json`.
No geometry or corpus change occurs during either continuation.

Added `scripts/rebin_commons_extension.py`: prepare only newly admitted train
sources at4×, then merge with the completed frozen base4× by reusing paths/hashes,
without copying old pixels. Both8× audit hashes and field-for-field preservation
of old records are required. Active source IDs/splits and credits must match;
reserved/excluded sources stay out. The merger checks actual NumPy shape/dtype
headers, producer ownership, full membership and source/selection recipes. It
publishes the audit before the final manifest and rejects frozen overwrite.
Producer checksums are retained; merge does not rehash the entire old corpus.

The one-worker new-source4× preparation is live under PID165067, implementation
archived before startup, with1,250 of1,808 sources and zero failures at the last
check. Workflow/log: `.cache/prepare_freeze_extension_four.py` /
`.cache/prepare-extension-four.log`. It waits on the already-live base-freezer
PID52903 before merging. Complete base4× preparation PID4128330 has passed19,700
sources, zero failures. Neither partial producer enters training. Expected future
expanded4× manifest:
`/mnt/external/demosaic/commons-extension-20261016-bin4-v1/audit/manifest.jsonl`.
The original downloader PID3989567 continues with its512GiB reserve; originals
and private photo trees remain read-only to preparation/training.

Added the gated V36 recipe, completing a two-by-two corpus/augmentation pilot:
V32 old8×, V35 expanded8×, V34 old4×→geometry→2×, V36 expanded4×→geometry→2×.
V34/V36 have not started; each future frozen-manifest path requires complete data.
Native4× retains exactly the same53 captures/31 scenes, and original8× validation
remains fixed in all arms.

Validation: **271 tests passed in40.91s**, including11 new preparation/merge
cases covering partial inputs, changed protected splits/attribution, duplicate
identities, incorrect pixel dimensions and competing owners. Ruff passed.
Four actual new-source4×→2× versus direct8× checks differ by at most one uint16
code before augmentation. Verified14 authoritative report-file hashes and52
native PNG hashes/dimensions, plus both new checkpoint hashes. Publication
checks caught a hash-field ambiguity: real-suite `source_sha256` describes
inference code. Added distinct `source_report_sha256` fields to all14 runs in
these three review receipts, preserving inference identities and numeric results.
Quality superiority, final-architecture DINO ablation, protected-final evidence
and<10s/100MP remain unproven; this progress does not complete the goal.
