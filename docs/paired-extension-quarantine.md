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
