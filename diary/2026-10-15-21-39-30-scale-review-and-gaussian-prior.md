# Scale-loss review complete; stronger frozen Gaussian flat prior

Both V26/V27 jobs stopped successfully at1000 steps (sessions45171/47792).
Evaluation68032 and flat/GFX65863 completed successfully. All41 sampled batch
hashes, CPU/Python/CUDA RNG states, initialization and archived source match.
Every original model/EMA value is bit-identical to V16. Actualschedule:530 paired
and470 Commons/procedural batches per arm. No protected final or GFX training.

Known/unseen primary PSNR53.27756/53.07374 for scale-aware loss, versus
53.26538/53.08259 control. Differences+.01218/−.00884dB, scene intervals
[−.00393,+.02431]/[−.01196,−.00635]. Synthetic64photoPSNR31.966864/31.966871,
effectively unchanged. Flat32/64 residuals barely change despite much larger
coarse-branch gradients. Neither promoted; V16 remains reviewed.

Published matched numerical/source/weight/ROI/noise/display receipts, two native
paired triplets per candidate and matched new-pair GFX foliage/fence views.
All four GFX regions ran with identical512px contexts. Visually reviewed paired
and GFX crops: texture loss and color speckling remain. These are crop-only
outputs; no new full-frame speed/quality claim. AHD/independent lowISO remain
approximate references. All196 tests passed before training; Ruff passes.

Inspected the Noise2VST ICCV2025 authors' MIT source at revision
02b839dae08e6304441ef9e5b3452262c36c4550 and acquired original KAIR weights
with MIT notices. Strictly loaded FFDNet-gray485316 and DRUNet-gray32638656
parameters. Source/weight/license hashes retained; no upstream code vendored
or dependency installed. Noise2VST adaptation itself was not executed.

A separate frozen DRUNet-gray probe denoises each Bayer phase independently,
then applies WB-aware Malvar. Same exact physical flat inputs/seed as the
residual diagnostic; sigma uses declared synthetic shot/read and observed
phase mean, no targets. IEEEFP32 and source-default normalization equivalence.
At level.01 residual centered sigma2.5983e-5 versus RawNIND8.1238e-5 and
V16 2.3195e-4; absolute bias7.5249e-6 versus4.4055e-5/4.8590e-5. This is a
strong flat diagnostic, not texture, demosaicing or photographic superiority.
No real GFX pixels fitted; only metadata defines synthetic camera transport.

Made `scripts/probe_gaussian_flat.py` reproducible with verified external
source, frozen weights, archived code/metadata/licenses and native exact-GT
triplets. Canonicalv2 rows exactly reproduce prototypev1. Published two native
triplets and receipts in `docs/gaussian-prior-probe.md`. All writes remain in
repo or/mnt/external; original photos untouched. Full quality/speed goals open.

Next available evidence-driven action: evaluate physical variance stabilization
and an appropriate bias-corrected inverse around a frozen Gaussian prior on
actual photographic crops, with explicit sensor priors and no target-assisted
inference. Preserve protected split/GFX restrictions and compare all methods on
identical inputs. Do not infer real quality from flat scores alone.
