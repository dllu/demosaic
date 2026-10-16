# More Commons images, prepared separately

The existing background QI downloader continues with three workers,0.5 requests
per second and a512GiB free-space reserve. A separately frozen selection contains
**11,952** newly downloaded, freely licensed candidates after excluding all46,738
identities in the preceding extension. Minimum original dimensions are2048px
per side; maximum decoded area is120MP. [Selection and live-job launch receipt](results/commons-incoming-v2-launch.json).

CPU-only preparation uses four workers, bounded row-band linear conversion and
8× area binning into
`/mnt/external/demosaic/commons-incoming-20261016-v2-quarantine/`.
The actual package and driver are archived there; later repository edits cannot
change the running data operator. These images are **not admitted to training**.
The producer's train/val/test fields are provisional.

After preparation and producer exit, a queued review verifies source hashes,
the standing GFX selection and42 cached protected references. It uses only cached
reference thumbnails for data identity screening, without model predictions or
protected-final performance scores. No source RAW is modified or reopened.

The new [screening operator](../scripts/screen_commons_protected.py) checks seven
whole/cropped views in all eight D4 orientations. Informative thumbnails within
4% aspect ratio are flagged at dHash distance≤40 or normalized correlation≥.95.
Standing capture IDs are blocked, including the old superseded pair; available
EXIF blocks the GFX100S date family. Unreadable metadata or invalid cache data
cannot silently clear a candidate. All positives stay quarantined. This finite
screen does not prove scene disjointness, particularly for heavily changed views
or missing metadata.

The duplicate audit then anchors the old extension's assignments, compares the
cleared candidates against its existing identities and perceptual fingerprint
cache, and reserves new buckets. Per-source screening outcomes are atomic and
resumable only with unchanged recipes/input identities. Cooperative locks prevent
concurrent writers; changed or frozen results refuse overwrite. Five targeted
tests pass, covering rotated matches, metadata exclusions, checksum/path failures,
locking and interrupted-run recovery; Ruff passes.

The queued workflow ends at `audited-quarantine8-awaiting-reviewed-freeze`.
Review its outcomes before publishing any separate frozen training extension.
Prepare matching4× caches for the current augmentation path and preserve the
existing validation/test identities before a new matched model trial. Running
and completed V47/V48 recipes retain their original40170-source Commons manifest.

## Completed8× review and4× preparation

The8× producer finishes with11,949 caches and three preparation failures.
Protected screening clears11,761 and quarantines188; all flags stay excluded.
Duplicate auditing admits10,558 new training images, reserves1,199 new holdouts
and excludes four duplicates. The separate reviewed8× corpus has52,536 training
images,2,303 validation and2,255 test images; old rows and evaluation membership
are exact. Relative to the current40,170 training recipe, this also includes
the earlier1,808-image extension. [Reviewed freeze and4× launch](results/commons-incoming-v2-reviewed8.json).

CPU-only matching4× preparation has started for only the10,558 newly admitted
images, reusing the previous46,536 active4× caches. All new cache SHA256s will
verify before the separate4× freeze. Its status is `rebin4-workflow.json` under
the quarantine root. The data are for a future matched trial; V49 and current
models keep the original data. The finite screening limitations still apply.
