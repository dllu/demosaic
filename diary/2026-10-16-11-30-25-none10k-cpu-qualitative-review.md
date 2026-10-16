# Completed first-arm CPU qualitative review without overlapping GPU work

Previous goal turn was progress: genuine ConvNeXt complete-state CPU restart
passed, deferred CUDA checks were prepared, and the original no-context arm
completed 10,000 updates with DINO-S actually resuming afterward. Revalidated
current files, live controller 164667/trainer 241003, their commands, finite S
metrics, downloader, memory and unchanged original/frozen source before work.

Added CPU FP32 support to the existing real-capture comparison helper. RawNIND
gain adapters accept the same selected device, while default GPU behavior stays
unchanged. CPU requests with half-precision labels fail before any input/output
or CUDA initialization. No production model/data math changed. Actual execution
and artifact checks replace unnecessary repeated unit suites for this helper
change; Ruff passes. The live workflow's frozen evaluation scripts still match
their pinned hashes.

Actually reran V43 and completed no-context10k EMA, plus both input-only RawNIND
calibration variants, on the fixed Q2/Sony/GFX50R caches: 24 native triplets and
21 unquantized float32 context arrays. No original photo directory was accessed.
Both learned models use CPU FP32 with matched coordinates/WB/matrix/exposure.
Created six direct learned comparisons from exact existing panel bytes.

Also replayed the two previously fixed README photo sources, one RGGB/high-noise
case each, with exact clean targets from the original 8×-binned data. Eight
triplets cover both learned methods and both RawNIND variants. CPU noise differs
from the earlier CUDA realization, explicitly recorded; no old scores reused.
Reconstructed/saved both observations and GT arrays with fingerprints and exact
source/ROI coordinates. The small two-case aggregate is not used for selection.
The first scratch artifact audit accidentally defaulted to the train split;
fixing it to val did not require any inference rerun. The completed audit passes.

All 38 PNGs were actually visually inspected. All panel geometry/hashes, 21 float
arrays, copied direct pixels and shared noisy/GT/comparator panels verify.
CPU rerendering from the real float arrays matches every panel byte exactly.
No CUDA context initialized; GPU training continues independently.

Findings: the two learned real-capture methods stay close, with soft Q2 shadows
and Sony window detail. Both show sharper GFX50R concrete seams/more variation
than RawNIND, without clean GT proving every fluctuation is signal. Fine cords
remain absent in the synthetic fabric example, with a more yellow/darker cast
in the fresh no-context crop. Both learned models preserve cleaner building
edges than RawNIND in the other example. This is no broad quality win or causal
ablation: V43's history and DINO differ. Keep V43/README unchanged and finish the
matched S/B/full numerical/analytic/GFX review before selecting a recipe.

[Review and native examples](../docs/cross-camera-none10k-cpu-review.md),
[complete receipt](../docs/results/cross-camera-none10k-cpu-review.json).
The standing DSCF3879/DSCF3880 sky/building/foliage/fence full-frame test remains
scheduled in the long workflow. Protected-final scoring remains closed; the
SOTA/real-quality/speed objective is still unproven and active.
