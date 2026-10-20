# Verify V43 fine-detail training and expand source review

Recorded: 2026-10-20T11:34:43-07:00 (America/Los_Angeles).

The quality-first data path now has a genuine discarded CPU training proof:
24 V43 optimizer updates, original EMA and full architecture exactly verified
before the first forward, all three training domains, three photographic
contrast attenuations and one weak-texture sample. Optical PSFs were forbidden.
Every forward made one actual DINO call; DINO remained frozen, model/EMA changed,
and gradients/optimizer/EMA stayed finite. CUDA remained uninitialized. The
B1/native32 checkpoint is discarded engineering output, not a new quality model.

A further 32-source visual review used six complete contact sheets and two
larger native1024 views. It retains31 and withholds one uncertain clean target
with visible edge halos/smoothed surfaces. Combined with the earlier31 sources,
58 of63 remain and five are withheld. Fine wheat, foliage, cloud gradients,
architectural seams and carved stone remain useful low-contrast detail. Physical
stained glass, photographed artifacts and botanical specimens are not discarded
merely for resembling graphics or having high loss. No originals were modified.

The corpus scan is still running. Curated manifests and production training
remain pending its final ranking and manual review. Speed work remains deferred.
See [the study](../docs/quality-first-training.md) for receipts and planned controls.
