# Whole-scene context and fine innovation validation

Recorded: 2026-11-16T23:37:51-08:00 (America/Los_Angeles).


The user directed attention to the historical whole-image production/context
review and emphasized the sky-versus-busy-fence ambiguity. Read the complete
review and checked current inference, pretrained RGB, DINO pyramid and data
sampling code. The hole remains real: DINO sees the tile, no scene preview/box.
The recent512/768 contexts do not supply whole-photo semantics. Prioritize the
[scene-context quality test](../docs/whole-scene-context-next-test.md) while
retaining local reconstruction and measurement-based fine phase/amplitude.

Implemented CFA-aware whole-observation preview and native-coordinate scene
feature sampling in scene_context.py. Eight tests pass: four actual CFA layouts,
shared calibration/aspect ratio, A-only withheld invariance, padded rectangular
geometry, crop-center coordinates, batch invariance, feature gradients and FP32 coordinates with FP16/BF16 maps.
No encoder/adapter integration, new DINO call or trained context gain claimed.
A full-RAW preview cannot condition an A→B evidence predictor without leakage.

Audited existing cleaned90781 Commons training records and32 eligible NPY
headers, source-drive/original photos untouched. Minimum cached short-axis
counts:51290781;76824746;10241759;153647;20483. Current extra2x reduction
shrinks those extents again. Existing source/crop provenance is usable, but
noise is generated after cropping and full-scene/crop noise alignment is absent.
The next generator must create one noisy complete scene and crop from it;
separate cohort changes from context changes with matched controls.

Before that steering, implemented the [A-only neural-parent fine innovation
validation control](../docs/parent-innovation-validation.md).114 relevant
regression tests pass. The default nuisance validation remains available.
Both frozen48-case producers completed before any new quality work:603.59s
original development/material/GFX,593.22s fresh coloured, two CPU threads each.
Zero new root/DINO forwards;88+96 genuine masked fields rechecked/audited.
All six numerical review stages pass; coloured208 rows/4368 independent fields
and40 fixed native figures are prepared. Actual native review/quality decision
remain pending, not a claimed improvement or whole-scene implementation.

The original procedural parent is V143 while its A-only teacher is V120;
the new coloured cohort uses V120 for both. Both protected GFX families remain
qualitative tests with independent ISO100/AHD/JPEG references, not exact GT.
No protected training admission, original-media writes, new noise or learned
weight update. Preserve executed sources/terminal receipts and pre-review state.
