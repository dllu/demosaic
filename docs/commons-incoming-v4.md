# Next Commons snapshot

A CPU job is preparing **10,024 additional downloaded images** into a separate
8× linear-light uint16 cache. The downloader continues in parallel. Existing
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

Operational files:

- Output: `/mnt/external/demosaic/commons-incoming-20261017-v4-quarantine/`.
- Controller: PID 1826191, creation 1792202173.31, with identity in `controller.json`.
- Status: `workflow.json`; selection and source hashes: `selection-recipe.json`.
- Log: `.cache/prepare-commons-incoming-v4.log`.
- Executed source: `source/`; independent startup auditor: `startup-audit-source.py`.

Inspect the current status and process before acting; do not launch a duplicate.
This preparation provides no restoration-quality result. The previous
[66,934-image 4× corpus](commons-incoming-v3.md) is already ready for a separate
matched data trial; the current experiment keeps its original 40,170 Commons
training images, 128 native captures and 32 paired sources.
