# Next Commons snapshot

The 8× caches and membership review are complete. The CPU job prepared
**10,022 of 10,024 additional downloaded images** into a
separate 8× linear-light uint16 cache; two failed. Its identity screen quarantined
126 and cleared 9,896. After preserving held-out assignments, **8,872** are new
training sources in a separate reviewed future corpus. Combined training count
is **75,806**; matching 4× preparation, complete independent pixel checks and
48-thumbnail content review are now complete. Active model inputs remain fixed.
[Reviewed 8× freeze](results/commons-incoming-v4-reviewed8.json),
[reviewed 4× corpus and independent receipts](results/commons-incoming-v4-reviewed4.json),
[actual 4× launch and startup checks](results/commons-incoming-v4-rebin4-launch.json),
[original producer completion](results/commons-incoming-v4-preparation-complete.json).
The downloader continues in parallel. Existing
training and evaluation manifests remain frozen, including the current batch16
model comparison. [Launch, frozen inputs and actual startup checks](results/commons-incoming-v4-launch.json).

Selection reads committed completed downloads from the live SQLite index,
materializes their metadata and closes the read connection before decoding.
There is no download-date cutoff. It excludes **74,935** identities from all
previous candidate sets and recorded preprocessing failures, including sources
that were previously quarantined. The original cache's fourteen failures add
fourteen exclusions beyond the earlier candidate sets; after excluding these,
this snapshot's downloads range from 2026-10-16 19:41:07 to 2026-10-17 01:56:15 UTC.
Every selected identity is distinct and absent from those prior sets. Selection
requires accepted CC BY, CC BY-SA, CC0 or public-domain metadata, at least 2048px
per side and at most 120MP. Source URLs, author, license, credit and attribution
are retained. Later arrivals cannot change this snapshot.

Preparation reuses the existing bounded row-band linear conversion and direct
8× binning, with **two CPU workers at nice 5** and CUDA hidden. Its estimated
cache payload is 11.88 GB (11.06 GiB), checked against available space and a
512 GiB reserve. Free space was about 1.18 TB at launch; the downloader also
enforces its own 512 GiB reserve. Preparation checks headroom before decoding
and before the audit stages; it does not continuously reserve disk space against
unrelated writers. Original files remain read-only. No personal RAW is opened.

The actual package, operators, standing-GFX config and driver were archived
before work began, and preparation imports the archived package. Independent
startup checks verify the complete selection, exclusion and source hashes;
all selected license/dimension metadata; and twelve published cache files'
full SHA256, uint16/HWC shape, minimum size and exact source fields. The producer
holds its preparation lock. At that check, **100 caches** had been published,
with no recorded failure. This verifies startup, not completion of all caches.

After preparation, the controller checks the **42 cached protected identity
references** and runs the existing seven-view/eight-orientation screen, including
the standing DSCF3879/DSCF3880 scene and sibling metadata exclusions. All flags
remain quarantined. It then audits duplicates against the reviewed 66,934-source
8× base, preserving old rows and held-out assignments and reserving new holdout
buckets. It stops at `audited-quarantine8-awaiting-reviewed-freeze`.
Complete cache verification and content review precede any reviewed freeze;
matching 4× preparation is also required for augmentation before final downsampling.
Finite identity screening cannot establish arbitrary scene disjointness.

The completion review independently verified every one of the **10,022** caches,
totaling **11.863 GB**, including full SHA256, uint16/HWC headers, minimum size,
binning recipe and exact source attribution against the frozen selection. Each
selected identity is prepared exactly once or recorded as one of two truncated
source-image failures. Every old row and held-out assignment is exact. All 126
protected flags remain absent; the near-duplicate audit excludes six new sources
and reserves 1,018 new holdouts. The separate reviewed 8× manifest SHA256 is
`05d152ef10a8f2aff7931756af54bae12c737eaad37f81c0f121eae0c5da008a`.

Three contact sheets covering 48 deterministically sampled new training sources
were actually viewed. They include architecture/interiors, foliage, sky/fog,
water/glacier, public portraits/sports, vehicles/trains, fireworks, electronics,
art and stone detail, without obvious broken decoding in the thumbnails. These
resized content previews do not verify native sharpness/noise or every scene.
Source identities, author/license/attribution and the manual review are retained
in the independent receipt. No protected RAW was opened or scored.

Matching 4× preparation selects only the **8,872** newly admitted training sources
and reuses the complete 66,934-source 4× base. It runs two CPU workers at nice 5,
CUDA hidden, a frozen package/operator/driver and a 512 GiB reserve. The first
12 4× caches pass SHA/header/recipe/source checks and a rounded area2 comparison
to the reviewed 8× pixels, within one uint16 code. This is a startup sample;
the complete check is recorded below. Original validation paths and both current
model inputs stay fixed.
Rebin controller PID 1953180, creation 1792206647.0; status
`rebin4-workflow.json`, plan `rebin4-plan.json`, log
`.cache/rebin-commons-incoming-v4.log`.

The [previously queued independent full 4× audit](results/commons-incoming-v4-independent4-queue.json)
is now complete, with its actual controller and producer exited. It rehashed
every one of the 8,872 new 4× and matching 8× files, checked uint16/HWC headers,
minimum size, source metadata and full membership, and retained all 71,492 base
rows and all 4,558 old held-out paths exactly. New 4× cache payload is 42.066 GB.
Across **5,253,613,515 channel samples**, rounded area2 reduction differs from
the corresponding 8× cache by at most one uint16 code (4,502,554,330 exact;
751,059,185 differ by one). All reserved/excluded rows remain absent.

Three 4× contact sheets covering 48 deterministic new training identities were
actually viewed: foliage/flowers, stone and stained glass, day/night buildings,
trains/platform fencing, people, vehicles, birds, coast/water, mountain, specimen
shells and interior detail. No obvious broken decoding or gross orientation/
channel corruption appears in these thumbnails; architecture is common in this
sample. Resized previews do not validate every image or native sharpness/noise.
The audit source, per-cache receipts, contacts, attribution and manual review are
retained. The separate `reviewed4.json` descriptor points to the checked manifest:

`extension4/audit/manifest.jsonl`, SHA256
`88f49cfc3a8a0a9fc74182a7f3fcd07b999f9153ae3dc8da54d72c6541890005`.

This future-stage corpus has 75,806 train/2,303 val/2,255 test rows. No active
model manifest is substituted and no new restoration score is computed.

Operational files:

- Output: `/mnt/external/demosaic/commons-incoming-20261017-v4-quarantine/`.
- Controller: PID 1826191, creation 1792202173.31, with identity in `controller.json`.
- Status: `workflow.json`; selection and source hashes: `selection-recipe.json`.
- Log: `.cache/prepare-commons-incoming-v4.log`.
- Executed source: `source/`; independent startup auditor: `startup-audit-source.py`.

Inspect the current status and process before acting; do not launch a duplicate.
This preparation provides no restoration-quality result. The current
[matched data trial](longer-commons-data-stage.md) uses 40,170 Commons training
images for V63 and the prior [66,934-image 4× corpus](commons-incoming-v3.md) for
V64, with the same 128 native captures and 32 paired sources. That experiment's
frozen membership remains unchanged by this new corpus.
