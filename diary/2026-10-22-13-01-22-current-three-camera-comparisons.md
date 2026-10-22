# Refresh real-camera comparisons with V84 and V100

Recorded: 2026-10-22T13:01:22-07:00 (America/Los_Angeles).

Previous turn made concrete progress: published fixed natural-detail inputs,
the V84/RawNIND reference and V100 final10000 comparison (commits19a7ee6 and
44b1a92). This turn revalidated the live V101 worker and existing broad
evaluation/full-frame queue controllers. No training was restarted or changed.

The current cross-camera guide still showed V43. Reused its existing six fixed
ROIs on the locally cached Q2 rocks/shadows, Sony a7R II fuselage and GFX50R
architecture captures. These were already development selections, not chosen
from new V84/V100 outputs. Exact source SHA256s/filenames are absent from the
active Commons/native/paired manifests; this is not a strict-unseen or complete
near-scene-independence claim. No source HDDs were read.

Ran the existing `compare_raw_crops.py` helper with frozen copied source,
V43/V84/V100 final EMAs and input-only CFA-channel RawNIND on CPU FP32.
All48 numerical modules match the source used by the natural-detail comparison.
The source-frozen plan is
`.cache/current-quality-20261022-v1/three-camera-v1/plan.json`;
outputs are `/mnt/external/demosaic/current-three-camera-20261022-v1/`.
Source/checkpoint bytes passed before/after guards; CUDA was never initialized.

The run writes18 native triplets and21 unquantized float32 contexts. Built and
actually viewed three native review boards (30 distinct cells), then rearranged
the same cells into three readable two-row public camera boards and actually
viewed all30 again at original resolution. A private publishing draft caught
an incorrect assumption about source-cell ordering before writing any board;
corrected it to the builder's case-outer/method-inner order. All saved board
cells match the source hashes. Rerendering all54 triplet panels from the retained
float32 contexts reproduces every RGB8 pixel exactly.

V84 and V100 look close. GFX50R concrete has finer surface variation/more
coherent joints in the learned outputs than RawNIND. Q2 dark rock structure
and Sony windows/fuselage remain soft, with no clear overall new winner.
These single captures have no clean reference or pixelwise quality scores;
RawNIND is explicitly labeled comparator/notGT. No full-frame or broad
superiority claim follows, and not every retained fluctuation is proven detail.

Published `docs/results/cross-camera-current-v1.json`, all18 source triplets
and three native boards under `docs/images/current-cameras/`. Rewrote the
cross-camera guide as current information, linked it from README/current-model/
GFX/docs-index, and preserved earlier machine receipts and historical images.
Corrected the stale current review counts in requirements/experiments to
530 reviewed,500 retained,30 withheld, distinguishing the24 exclusions applied
to active runs from the six prepared for the next cohort.

Final checks passed:48 bound receipt references,18 source triplets and sidecars,
all30 published native-cell hashes and updated local documentation links.
All five source/input plans pass guards. The V101 worker and both downstream
controllers remain live; the broader goal and quality work remain active.
