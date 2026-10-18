# Mature full-frame FP32 autotuning reaches the actual CLI

Completed the mature-reference full-frame comparison, two fixed exact-GT photo
checks per checkpoint, and verification through the real new CLI on the cached
DSCF3879 RAF. No training/model/default change. The project quality and sub10s
objectives remain unmet/unproven.

Warmed original→autotuned restores are206.8819→118.2165s for V43 and
209.3524→120.4780s for V63, one shared-machine observation each,512/64/B4,
IEEE FP32 without AMP/TF32. Initial search/library forwards are21.7340/22.9186s,
reported separately, not described as pure search overhead. All611,975,112
unquantized RGB values pass unchanged1DN16 max/.25DN16 RMS limits; independent
float64 reductions agree. Both complete candidate linear16 exports match
their declared quantizers. Actual model/DINO/checkpoint/source/RNG stay fixed.

Added opt-in `infer --cudnn-benchmark`: limit10,16GiB allocator cap preserving
stricter quotas, FP32-only, restoration of backend/precision/quota on exit/error,
and sidecar settings. The first harness failed before CLI or inference because
the actual PyTorch quota getter rejects bare `cuda`; fixed the helper to resolve
the active device index and added a strict regression. The failed v1 plan/source
and exact observed error remain preserved. Twenty targeted CPU tests pass;
production/test Ruff passes. Frozen experiment code has an unrelated unused
local; its signed bytes remain unchanged rather than claiming strict Ruff there.

Corrected real CLI proof succeeds. Every305,987,556 F32 value passes the original
limits against original V43, max.105467/RMS.000779DN16. Both entire TIFFs match
linear/sRGB16 quantization and metadata; preview ICC verified. Actual backend
settings and quota restored. Its fresh restore is166.6736s including search;
instrumented end-to-end178.2012s includes additional capture/hash/save work,
so neither is substituted for the warmed118.2165s scope.

Actually viewed all16 full-frame GFX triplets/24 unique native cells, including
sky/building/foliage/fence, and all8 exact-GT photo triplets/12 cells. No visible
policy differences. Mature outputs remain soft in foliage and canopy cords;
V43/V63 tone differences are not corrected. The two photo observations use
fixed existing CPU-generated ISO12800/RGGB noise, B1/native256, shared WB/matrix,
exposure1 and native160 ROI. All786,432 values pass original limits, independent
arithmetic included. Real GFX uses exposure4/+2EV and separately demosaiced
ISO100/f5.6 DSCF3880, correctly labeled a reference rather than GT.

Published [full report](../docs/mature-cudnn-fullframe.md) and
[complete registry](../docs/results/mature-cudnn-fullframe-v1.json), ten exact
PNG byte copies, full boards and two GT/foliage/fence triplets per checkpoint.
README now uses four representative new FP32 triplets and an explicit opt-in
FP32 command. Updated the living experiment/training indexes to the completed
160k review: own-parent gains, losses to older equal-example controls, no
promotion. Earlier closed reports and their hashes remain preserved.

Reclaimed2.476593GiB by replacing five completed owned duplicate V43 evaluation
snapshots with links to the existing immutable cache. Original checkpoint inode,
permissions, bytes and214 report/image/metric hashes stay unchanged. Independent
audit and [storage receipt](../docs/results/completed-quarter-V43-storage-v1.json)
record the checks. No original weight/photo or F32/TIFF was deleted. External
free space remains about502GiB, so leave the reserve-stopped QI downloader off.
All experiment workers/controllers have exited. No automatic extension of the
grainy10k RAW pair; a further quality trial needs a specific controlled rationale.
