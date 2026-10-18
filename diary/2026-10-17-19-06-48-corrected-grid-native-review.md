# Completed corrected-grid native review

Reviewed all36 predetermined actual40k CUDA triplets at native160px:12 exact
synthetic-GT photographic triplets and24 GFX independent-reference triplets.
Six boards copy original panels without resizing, verify all source hashes and
check shared noisy/reference pixels. Published eight triplets and two native
edge boards with full source/ROI, checkpoint, noise and display metadata.

Alignment reduces whole-context RMS from79–83 to9.5–14.5DN16 without DINO
and129–136 to69.5–77.7 with DINO, but still fails strict equivalence and
slightly lowers the selected exact-GT photo scores. Native views retain grain,
soft foliage and uneven mesh. Changed-edge crops show no obvious improvement or
regression at the selected scale; that is not an all-frame invisibility claim.

Full101.995852MP corrected restore medians are54.436s and53.749s, each
three repeats after one excluded full warmup. Repeat arrays are bitwise equal.
Every corrected RGB16 pixel reproduces its saved F32 prediction's export;
all305,987,556 old/new channel values are compared per model. Export differences
are not unclamped F32 equivalence or real-GT error. The independent ISO100
capture remains accurately labeled, and no original source is modified.

The original plan and full40k review remain immutable. The automatic workflow
status predates this separate manual receipt; its guarded status file is left
unchanged. Neither40k model is promoted; overall quality and10s goals remain open.
Ten published asset copies and local documentation links verify; git whitespace
checks pass. No new inference was needed for this manual review.

A separate four-arm fresh-model CUDA optimization diagnostic is running, with
all learned weights to be discarded. It does not alter these checkpoints,
observations or conclusions. The existing isolated CPU diagnostic also continues.
