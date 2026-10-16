# Preparing the next Commons arrivals separately

The 8× preparation and audits are now complete. A separate reviewed future
corpus contains **66,934 training sources**, including **14,398** newly admitted
images. Matching 4× preparation is running; all current model manifests remain
fixed. [Reviewed freeze](results/commons-incoming-v3-reviewed8.json),
[actual 4× launch](results/commons-incoming-v3-rebin4-launch.json).

The background downloader remains live. A new CPU job has frozen **16,231**
additional downloaded candidates for preparation and identity screening.
[Actual launch, exact selection/operator hashes and startup checks](results/commons-incoming-v3-launch.json).
These data are not admitted to any model. The original no-context/S/B trial
keeps its fixed Commons 40,170/native 128/original paired 32 recipe.

The selection excludes **all 58,690 identities** from the original extension
and the previous incoming selection, including earlier quarantines and
preparation failures. It selects only completed downloads with accepted CC BY,
CC BY-SA, CC0 or public-domain metadata, at least 2048px on both sides and at
most 120MP. Full source URLs, author/license/credit fields and source identities
are frozen in the selection. Later arrivals cannot change this job's members.

Preparation uses two CPU workers at nice 5, bounded row-band linear-light
conversion and direct 8× binning to uint16. Estimated cache payload is 18.47 GB
(17.20 GiB), checked against available space and a 512 GiB reserve before launch.
The existing downloader retains its own 512 GiB reserve. The preparation process
was observed using about 1.16 GB RSS; this is an observation, not a peak-memory
benchmark. Original Commons files remain read-only. No personal RAW is read.

After preparation returns and releases its cache lock, the same controller:

1. Checks the frozen standing GFX selection and 42 cached protected identity
   references, without opening protected RAWs or computing model predictions.
2. Runs the existing seven-view/eight-orientation perceptual/metadata screen.
   Every flag stays quarantined, including the standing capture/date family.
3. Runs the existing near-duplicate audit against the separate reviewed 8×
   52,536-training-source corpus. Old source/split assignments stay anchored;
   new validation/test buckets stay reserved outside active evaluation.
4. Stops at `audited-quarantine8-awaiting-reviewed-freeze` for review before
   publishing any new training manifest. Matching 4× caches are still required
   for the current pre-final-downsampling augmentation path.

The finite identity screen does not prove scene disjointness under arbitrary
crop/viewpoint changes or missing metadata. This launch is data preparation,
rather than evidence that more sources improve restoration. The previous
[V50 corpus trial](commons-expanded-v50-review.md) did not establish such a gain
at its first gate; the ongoing fresh-model comparison remains controlled.

The actual package, operators and driver are copied into the output before
processing and loaded from that archive. Repository edits cannot change the
running preparation or queued screening. All selection identities are distinct
from the full prior candidate set. The first twelve successfully published
caches pass full SHA256, uint16/HWC/size/shape/recipe checks. This is a startup
sample, not verification of every future cache. The completion checks below
supersede that launch-only sample.

Operational files:

- Controller PID 335495, creation 1792179662.9; live identity recorded in the receipt.
- Output `/mnt/external/demosaic/commons-incoming-20261016-v3-quarantine/`.
- Controller/status: `controller.json` and `workflow.json` under that output.
- Log `.cache/prepare-commons-incoming-v3.log`.
- Frozen `selection.jsonl`, `selection-recipe.json` and `source/` under the output.

Inspect the live process/status/log; do not launch a duplicate. All original
training/evaluation manifest hashes still match, and no CUDA work was started.
The final executed launcher passes Ruff; the reused preparation/screening/audit
operators retain their existing validation. This job does not create a new
model, performance score or README reference.

## Completed 8× review and matching 4× preparation

The producer completed 16,230 caches, totaling18.45 GB, with one ICC-transform
failure explicitly excluded. An independent read-only pass verified every
cache's full SHA256, uint16/HWC shape, minimum size, binning metadata and exact
source attribution against the frozen16,231-source selection. Every selected
identity is either prepared once or recorded as that single failure.

Protected screening clears16,001 and quarantines229; all flags remain absent
from the expanded membership. Near-duplicate auditing adds14,398 training
images, reserves1,592 new holdouts and excludes11 near duplicates. Every old
row and validation/test assignment is exact. The reviewed8× manifest SHA256 is
`01cb4185d3ea7577939981662e3cf9c8aefc9764260ff6fd2b3b334c7cf78894`.

Three resized contact sheets containing48 caches were actually inspected from
a recorded partial15,382-cache snapshot;44 are now admitted new training
sources. They include architecture, interiors, foliage, wildlife, transportation,
night scenes and a portrait, without obvious broken decoding in the thumbnails.
This is a content spot-check, not native-quality verification of every source
or a complete scene-overlap proof. All protected flags stay excluded regardless
of this preview review. The standing GFX scene/siblings remain excluded.

CPU-only4× preparation now processes just the14,398 new training sources,
reusing the existing52,536-source training base and its held-out cache paths.
It uses two workers at nice5, a frozen package/operator/driver and an estimated
66.8 GB payload checked against a512 GiB reserve. All new cache SHA256s must
verify before the combined4× manifest freezes. The final active counts must be
66,934 train/2,303 val/2,255 test; new reserved/excluded sources stay outside it.
The original8× validation manifest remains the evaluation input for future
augmentation trials.

Rebin controller580845, creation1792185684.87, owns
`rebin4-workflow.json` and `rebin4-controller.json` under the quarantine root.
Its log is `.cache/rebin-commons-incoming-v3.log`. The process archives its exact
operator/driver under `rebin4-source/` and imports the already frozen package
from `source/`. It cannot silently absorb later downloads or change the running
ConvNeXt trial's40,170-source training manifest. No quality gain follows from
preparing more images; a sufficiently trained comparison remains necessary.
