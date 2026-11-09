# Consolidate inactive project archives and recover disk space

Recorded: 2026-11-08T18:19:00-08:00 (America/Los_Angeles).

The user requested stale-file cleanup and offload to `/mnt/external` as needed.
Both drives began at 97% use. The local historical archives had already received
the earlier same-day consolidation; this pass focused on remaining copies and
project-owned external archives before allocating offload space.

Completed actions:

- Consolidated 217 local groups and 11,612 external groups using full SHA256 equality. Reclaimed 0.135 GiB locally and 133.589 GiB externally. Preserved all 42,761 artifact paths and bytes; shared artifacts are read-only.
- Offloaded 93.092 GiB of old full-frame NumPy/TIFF renders: 126 unique files, 127 original file paths. Individual file symlinks retain original-path access; all directories remain local. Destination: `/mnt/external/demosaic/cold-full-frame-20261108-v1/`.
- Removed seven inactive generated pytest/compiler directories (170,074,112 exclusive allocated bytes) and the package download cache. The package cache tool's 5.3 GiB logical count mostly represented installed-package hard links; the independently inventoried minimum exclusive allocation was 125,231,104 bytes. Do not add 5.3 GiB to physical savings.
- Verified 17,443 pre-existing tracked file hashes unchanged, with the storage guide intentionally updated. Preserved 87 bindings for existing uncommitted V200 publication work and checkpoint/export files. All 36 protected GFX cache file metadata records match, and both photo caches remain local real directories.

After verification, local availability was **230.424 GiB**, versus
137.299 GiB initially. External availability was
**151.874 GiB**, versus 111.377 GiB initially.
The repository's local allocation is 451.088 GiB.
Free-space deltas also include concurrent projects and operation/Git records.

Eight compaction policy/full-hash/changed-input/unknown-alias tests and three
offload reader/copy-failure/changed-source tests passed. Every consolidated group
was rehashed during application and every alias checked again at completion.
Every offloaded file passed full byte-hash checks and NumPy/TIFF reader checks
through its original path. The installed Torch/NumPy/TIFF/Pillow/psutil imports
passed after package cache removal. No training or inference was performed.
No original photo storage was accessed or modified.

The relocation map records old/new paths, hashes and original inode metadata.
Strict historical readers comparing resolved path strings must use this map;
ordinary original-path reads preserve content. Make a separate writable copy
before changing a shared archive or resuming from it.

[Verified receipt and operation evidence](../docs/results/storage-maintenance-20261108-v2.json).
[Current storage guide](../docs/storage.md).
