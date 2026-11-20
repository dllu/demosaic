# Test weak phase transport through curved RAW detail

Recorded: 2026-11-20T05:06:58-08:00 (America/Los_Angeles).

The [curved phase transport report](../docs/local-curved-phase-transport.md)
compares fixed, refined planar and curved exterior phase, with a separate
opposed-pair and single-donor check. Two donor folds have to predict
measured Bayer samples before the query can use the fitted geometry. The
prior per-crop weak and fixed phase results reproduce exactly. On 24 new
source-disjoint curved scenes, phase agreement rises from 0.799 to 0.999
on the 15 comparable sources. The curved taper gains 0.102 weak-response
points over fixed phase with an interval spanning zero and changes added
gap texture at equal recovery by −0.003 DN16.

A follow-up refits the local weak basis using the exterior geometry. It
adds 0.053 points over the taper on the same 24 scenes with essentially
equal added gap luma RMS. This is a discovery diagnostic on those inputs.
Most of the response difference still comes from the weak-only correction
already present in the parent pipeline.

Both native GFX families were reviewed. The [main scene](../docs/gfx-qualitative.md)
keeps smooth sky and coarse crossings. On the [fine cab mesh](../docs/gfx-green-mesh.md),
only one donor has repeatable weak evidence for the right crop, and the
extrapolated phase disagrees between donor folds. Both cab priors use the
uniform fallback. Two native triplets per experiment and refit were viewed.

The replay uses frozen checkpoints. The primary panels in the
[PSNR history](../docs/performance-history.md) fall outside this crop study.
[Receipts, native metadata and source bindings](../docs/results/local-phase-transport-v2/publication.json).
