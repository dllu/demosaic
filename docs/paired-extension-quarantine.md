# Additional public paired RAW scenes

The frozen [RawNIND publisher catalog](https://doi.org/10.14428/DVN/DEQCIM)
contains59 eligible new scene candidates after conservative metadata exclusions:
231 RAW files,11.03GB. This can broaden the current32-scene paired supervision,
but **nothing is admitted to training yet**.
[Selection and provenance](results/paired-extension-quarantine-plan.json).

The downloader keeps the original fixed training allowlist intact. It excludes
all cached protected scene identities, existing32 training names/source hashes,
official test reserves/TEST filenames, unknown sensors, and entire MuseeL-,
LucieB_,7D-,D60- and boardgames_ families. This also excludes nearby views such
as boardgames_bot when boardgames_top is protected. New scene aliases sharing
protected/existing/selected source SHA1s are excluded. Selection uses metadata
only: up to two filename-ordered clean frames, noisy ISO nearest1600 and highest
remaining ISO≤12800. All new records explicitly carry split=quarantine.

The dataset release is CC BY-SA4.0. The plan retains per-scene permission text;
four selected scenes have explicit CC0 grants,55 use the dataset grant. Any
non-CC0 scene override is rejected rather than inheriting the dataset license
over that override. Existing publisher metadata, descriptor and permissions
are pinned; the latter two verify the publisher's file checksums. Every RAW
must verify size, publisher checksum and source SHA1, then records SHA256.
Sources/permissions/catalog and acquisition code are archived locally.

The downloader is lock-protected, resumes verified files, refuses a changed
plan, uses one worker and retains512GiB free space. All writes are under
`/mnt/external/demosaic/paired-extension-20261016-quarantine-v1/`; source photo
directories are not used. It runs separately from GPU training; active recipes,
holdouts and the GFX exclusion stay fixed.

```bash
source scripts/env.sh
uv run --no-sync python scripts/fetch_paired_extension.py \
  --output /mnt/external/demosaic/paired-extension-20261016-quarantine-v1 \
  --workers 1 --reserve-gib 512 --download
```

Before any future opt-in training extension, check both clean references against
cached protected views and the Commons val/test sources, inspect scene content,
decode camera metadata, and review registration/valid-reference coverage. Clean
RAW references retain noise; independently demosaiced RGB is auxiliary, not
exact GT. Quarantine preparation must preserve its split and cannot be loaded
by the current `PairedDataset` training guard. Frozen development/final data
cannot enter the extension. The finite identity screen is not proof of complete
scene separation. Downloading or preparing data alone establishes no model gain.

Sixteen targeted acquisition/selection tests pass: original paired acquisition
tests plus new metadata-only/quarantine/split/family/source-alias/license tests.
No enlarged full-suite count is claimed from this separate invocation.

The [background acquisition](results/paired-extension-download-launch.json) runs
from frozen `e2db058`. The new screen checks **both** clean references against
all42 cached protected RAW/GFX views and all4,558 Commons val/test images.
Both sides use seven full/center/corner views and eight dihedral transforms;
aspect4%, dHash≤40 OR correlation≥.95 flags hold the whole scene. Uninformative
or unidentified-camera references are held. Source/cache hashes, duplicate IDs,
safe ledger names, locks, frozen recipes and interruption reuse are checked.
Flags remain quarantined for review; no scoring model is loaded.

[The actual two-scene pilot](results/paired-extension-pilot.json) decoded Canon
EOS6D Bark and Blombukett, passed the identity screen, registered four noisy
pairs and verified36 fixed512px crops. All prepared records retain quarantine.
The ordinary-Bayer decoder preflight reports RGGB/3670×5496 for Bark. A separate
preparer records failed scenes, verifies every NPZ's hash/dimensions/native
float32 data/measured-reference mask, and preserves per-scene outcomes for
restart. Screen-clear or successful preparation is not training admission.
Eleven targeted screening/preparation tests pass separately from acquisition.

These resized contact images are for dataset content inspection:

![Bark texture and indoor flower bouquet](images/paired-extension-pilot-content.jpg)

Native160px data/registration pairs, **noisy Malvar → independent AHD reference**,
shared+1EV and fixed ROI[176,176,160,160] inside the center512px prepared crop:

![Bark native data pair](images/paired-extension-pilot-bark-native.png)

![Blombukett native data pair](images/paired-extension-pilot-blombukett-native.png)

These are not learned-model outputs or exact-GT comparisons. The high-ISO frames
are ISO12800; source/ROI/registration/noise/display settings are in the receipt.
Per-series apertures match (f/7.1 bark, f/4 bouquet), but low-ISO exposures are
1/4s and0.4s versus1/500s and1/320s. Scene movement and reference sharpness need
further native review before admission. Both scenes have CC0 grants by Peter
Wemmert; source RAWs are read-only and preview transforms are disclosed.
