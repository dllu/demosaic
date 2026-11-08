# Preserve evidence while reclaiming frozen-source storage

Recorded: 2026-11-08T11:17:05-08:00 (America/Los_Angeles).

After V193 publication and the final Git commit, local free space was40.0003GiB, almost exactly the completed experiment's40GiB runtime floor. All scientific owners were already terminal. No original, media, prediction, checkpoint, PNG or experiment receipt was removed or rewritten.

Nonpruning Git maintenance used `git -c gc.reflogExpire=never -c gc.reflogExpireUnreachable=never gc --prune=never`. Before/after comparison preserved every one of25367 reachable/unreachable object IDs, every reference, HEAD, index and all17 reflog byte hashes. Full fsck passed. This reclaimed13.54MiB, insufficient for another model allocation.

A separate read-only inventory found repeated immutable Python snapshots under local`.cache/*quality*` frozen work/src/scripts/tests directories. The subsequent plan grouped only files with identical SHA256,size,mode,uid,gid andmtime_ns, each initially a single-link inode; canonical files and all non-Python artifacts were excluded. Atomic hardlinks replaced duplicate physical copies while keeping every original path and byte. Affected source groups are recorded exactly in the receipt:3091 groups,25302 duplicate path replacements,293.203MiB expected reclaimed file blocks. Inode/link-count/ctime changes are the intended physical storage change; original mode/ownership/mtime and all hashes remain exact.

The post-check rehashed every selected path, all103 canonical neural sources and every sealed V193 frozen file/input binding. All pass. Local free space returned to40.2966GiB before this small documentation commit. Public compressed plan, applied-group journal and result retain full mappings and before-state metadata. This does not rerun any model or scientific prefix and does not lower a resource floor. The small, already prepared V194 orientation diagnostic can proceed on saved predictions; larger model allocations still need a conservative prospective storage budget. The fine-real-detail/flat-field goal remains open.

[Git preservation receipt](../docs/results/v193-git-storage-maintenance-v1.json) · [Frozen-source storage receipt](../docs/results/v193-frozen-source-storage-v1.json) · [Completed model comparison](../docs/large-dense-spectrum-comparison.md).
