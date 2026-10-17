# Preserve learned sampling grids at final tiles

Found and corrected a real geometry issue while the original matched RAW trials
continue. Even tile starts preserve Bayer phase, but the packed trunk also has
a native4-pixel grid. Its frozen ConvNeXt pyramid has a32-pixel grid. The old GFX
last row starts at8234 (8746 minus512), shifting both grids. The corrected starts
are8236 without DINO and8256 with DINO. Inputs extend whole CFA cells; native
coordinates and returned dimensions remain unchanged. Strides round down to the
model grid to preserve at least requested overlap. Other architectures retain
legacy geometry. Both GFX packed variants still use520 tiles at512/64.

The regression uses the actual packed trunk with a known4-period residual over
a flat colored CFA field, without spatial filtering. The archived old inference
fails with a.003 camera-linear error. The fix passes even/odd rectangles,
unrounded overlap requests, a32-period context fixture, legacy geometry and
invalid requests. Final focused CPU suite:56 passed,2 CUDA-only skips in7.32s.
Ruff formatting/checks pass. The initial test constructor omitted the required
camera-conditioning option; correcting the fixture then reproduces the real
phase failure. No training or model option changes were needed.

Actual no-DINO24k and genuine pinned-DINO8k CPU checks use two cached realGFX
966x962 contexts. Correct-grid interior RMS disagreement against whole-context
inference falls18.878/19.313 to2.635/2.640 DN16 without DINO, and19.072/24.462 to
6.586/7.095 with DINO. Different model budgets/context origins prevent a DINO
ablation claim. Aligning only4 for DINO is not its encoder grid and does not
resolve the context/padding differences. Whole-network output is not GT.

A separate no-DINO overlap224 diagnostic lowers RMS to.460/.582 DN16 but still
has maxima30.05/52.66 DN16. Overlap64 remains default. This is not a proof of
whole-image equivalence or a new inference-speed result.

Two additional held-out8x-binned photographic targets have fixed CPU native510
Poisson/read/ADC observations. Previous/correct-grid sRGB PSNR is24.46316 vs
24.45741 for the cyclist,24.09717 vs24.09197 for the roof. These small regressions
supply no restoration-quality gain. They are not the official427 GPU panel.

The actual corrected tiler is bitwise identical to independently phase-padded
old-operator outputs on six trained CPU restores: two GFX regions for each
checkpoint plus those two photos. Every model tensor byte and parameter ID,
including genuine frozen DINO weights, remains unchanged. All physical model
modules match the frozen old source. Only inference.py geometry changes.

I inspected and published twelve native100% triplets: both photo targets and
GFX foliage/fence for each checkpoint, before/after the correction. Metadata
records sources, source/context/ROI coordinates, checkpoint hashes, conditioning,
WB/matrix/exposure and observation hashes. ISO100 references remain accurately
labeled independent captures, not GT. Neither model's substantial noise and
soft-detail limitations is repaired. Working V43/README remain unchanged.

Public note: docs/packed-isotropic-tile-grid.md.
Public receipt: docs/results/packed-isotropic-grid-fix-CPU-v1.json,
SHA a09802dddc956e6bd4a84e29a66e5c5f21a6831535ae5f793cbd323baa108b1a.
Actual corrected CPU replay/integration and regression proof:
/mnt/external/demosaic/benchmarks/packed-isotropic-grid-fix-integration-CPU-v1/.
Private old-source GFX/photographic operators, full float arrays and receipts
are retained in the three tiling-CPU-v1 directories bound by the public receipt.
No original photo drive is read or modified and no GPU job is added.

All three live controllers and49/167/159 guards plus19/48/19 inputs were rechecked.
They retain their immutable old geometry; the queued40k quality and compilation
results must carry that protocol label. New corrected-grid CUDA/full102MP native
validation remains before any packed-model/policy promotion. The complete
PROMPT.md quality and speed objective remains unmet.

At 2026-10-17T16:19:25.183884-07:00, the no-DINO training log has reached step36600.
