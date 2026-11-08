# Reclaim duplicate historical storage

Recorded: 2026-11-08T12:04:58-08:00 (America/Los_Angeles).

The user requested disk cleanup and offloading as necessary. Paused experiment
execution during maintenance. The project occupied approximately 658 GiB, with
most space in the older current-quality-20261023, quality-20261102 and
quality-20261103 cache trees; local availability was approximately 33 GiB and
external availability 111.377 GiB.

Reclaimed **114.534 GiB** without offloading: 4.301 GiB from 34 inactive generated
pytest/compiler cache directories (37,764 files), and 110.233 GiB by consolidating
fully SHA256-verified identical historical artifacts. The consolidation covers
5,892 groups and 30,293 retained paths, with 23,438 atomic replacements. Major
savings were 53.875 GiB of repeated JSONL manifests, 49.426 GiB of NumPy arrays and
archives, and 6.194 GiB of checkpoint snapshots. Every unique artifact survives.

Selected roots were `.cache/current-quality-20261023-v1`,
`.cache/quality-20261102`, `.cache/quality-20261103`, `.cache/experiments`,
`.cache/benchmarks` and `.cache/quality-first-20261020`. The driver excludes
symlinks, files modified within two days, small files and inodes with unknown
aliases. It checks workers/open files, hashes complete candidate contents,
checks identities against the sealed plan, journals intent, atomically links
duplicates, and rehashes resulting groups. Shared historical files become
read-only and acquire the anchor's mtime/inode; original metadata remains in the
compressed plan. Copy before editing or resuming from shared historical files.

Manual isolated fixtures checked duplicates, distinct content, unknown aliases,
read-only sealing and rejection of changed inputs before mutation. Ruff and
`git diff --check` passed. Completion verification checked all 30,293 aliases,
eight V187/V193 export/source-checkpoint bindings, 906 V193 and 11 V195 sealed
bindings, and 103 unchanged neural sources. No training, inference or quality
measurement was repeated. Existing receipts and experiment bytes survive.
Protected GFX caches remain real local directories; originals were not accessed.

Project allocation after verification was 542.745 GiB and local available space
146.821 GiB. Other projects can change filesystem availability concurrently.
External storage was unchanged. Added a reusable plan/apply driver and a storage
guide recommending reuse of immutable manifests, datasets and model snapshots.

[Public receipt and compressed evidence](../docs/results/storage-maintenance-20261108-v1.json)
and [maintenance guide](../docs/storage.md). Private working evidence is in
`.cache/storage-maintenance-20261108-v1/`. Historical bytes/paths and Git history
were preserved; only disposable generated caches were removed.
