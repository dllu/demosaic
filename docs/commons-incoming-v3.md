# Preparing the next Commons arrivals separately

The 8× preparation, audits and matching 4× preparation are complete. A separate
reviewed future corpus contains **66,934 training sources**, including **14,398**
newly admitted images. Both complete caches are ready for a separate data
comparison; current model manifests remain fixed.
[Reviewed freeze](results/commons-incoming-v3-reviewed8.json),
[completed 4× verification](results/commons-incoming-v3-rebin4-complete.json).
The [next 10,024-source snapshot](commons-incoming-v4.md) has a reviewed 8× freeze;
its matching 4× preparation runs separately.

The background downloader remains live. This completed CPU job froze **16,231**
additional downloaded candidates for preparation and identity screening.
[Actual launch, exact selection/operator hashes and startup checks](results/commons-incoming-v3-launch.json).
These data are not admitted to any model. The original no-context/S/B trial
used Commons 40,170/native 128/original paired 32; the current palette comparison
retains that fixed data recipe.

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

The completed producer and rebin controllers have exited; do not restart them.
All original training/evaluation manifest hashes still match, and no CUDA work
was started by this preparation.
The final executed launcher passes Ruff; the reused preparation/screening/audit
operators retain their existing validation. This job does not create a new
model, performance score or README reference.

## Reviewed 8× and completed matching 4×

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

CPU-only4× preparation completed all 14,398 new training sources, totaling
65.250711758 GB, while reusing the existing52,536-source training base and its
held-out cache paths. It used two workers at nice5, a frozen package/operator/
driver and a 512 GiB reserve. The producer finished and exited; its full checksum
verification and merge froze66,934 train/2,303 val/2,255 test. New reserved and
excluded sources remain outside this separate corpus.
The original8× validation manifest remains the evaluation input for future
augmentation trials.

[Complete producer, independent audit and content-review receipt](results/commons-incoming-v3-rebin4-complete.json).
The frozen4× manifest is
`/mnt/external/demosaic/commons-incoming-20261016-v3-quarantine/extension4/audit/manifest.jsonl`,
SHA256 `7ed635903e4dd698081475a3667c8a14bb3b9f5f628a0917a5e336406faaecde`.

An independent read-only pass rehashed **every new 4× and matching 8× cache**,
verified uint16/HWC/shape/minimum-size metadata, and compared rounded2× area
means from the4× caches to their reviewed8× pixels. Across 8,148,865,503 channel
samples, differences are bounded by **one uint16 code**; 6,987,813,188 match
exactly. This checks the content and expected quantization relationship, without
interpolation or source-image rewriting. All 57,094 reused base rows, including
4,558 validation/test cache paths, remain exact. Every active source/attribution
field matches the reviewed8× membership; reserved/excluded sources stay omitted.

Three new resized contact sheets covering 48 evenly spaced training IDs were
actually viewed. They include architecture, night scenes, skies, foliage,
wildlife, art, products, vehicles/sports and a diagram. No obvious broken decode
appears in these previews. This remains a content spot check, rather than native
visual verification of every cache or a complete scene-identity proof. The
existing protected-screen flags and standing-GFX camera/date/identifier
exclusions remain in force.

The completed rebin controller was580845, creation1792185684.87. Its exact
operator/driver remain in `rebin4-source/`, the package in `source/`, and the log
in `.cache/rebin-commons-incoming-v3.log`. The independent audit and per-cache
records are in
`/mnt/external/demosaic/benchmarks/commons-v3-4x-complete-integrity-v1/`.
Neither the current40,170-source training manifest nor original validation
changed. The new corpus is ready for a separate data comparison; preparing more
images does not establish a trained quality gain.
