# Protect full-review export headroom

Previous goal turn made concrete progress: shared immutable checkpoint cache,
actual cross-process checkpoint proof,22 passing tests and pushed83260fb.
Revalidated current owners by PID and creation time. Original no-DINO child
2645905/1792305192.6 remains live under2645898/1792305192.32, advancing from
7250/116000 to7525/120400 updates/examples, approximately1.09s/update.
Quality2667688/1792305841.61 and profile2714232/1792306477.92 remain queued,
child-free. No active source, plan, recipe or job restarted/changed.

Reviewed the completed primary/full-GFX/hue/highlight output sizes because
free519.40GiB was close to the upcoming500GiB reserve. Independent per-path
allocation, counting repeated snapshot paths rather than allowing du to elide
hardlinks, totals16.40142GiB for the preceding same-shape review. Remaining
archives and temporary save space also need headroom. New cache code applies
only to future evaluations; frozen queued workers retain their old behavior.

Found another11.220378876GiB in identical checkpoint snapshots across six
completed owned reviews. Prepared and checked46 replacements over11 digests,
all original archives physically separate, all terminal producers exited.
Plan SHA499b203a53d101020f8f237cab74a7f9d1e06e66334b120a9baa856ae7ef3cb1.
Applied only those replacements via checked links and atomic replacement,
retaining a rollback link until each post-check passed. Canonical evaluation
inodes are read-only. All61 snapshot paths retain exact bytes/hashes and all11
original archives retain their bytes, permissions, timestamps and inodes.
No source, photograph, model archive, metric, image or active file deleted.

Private driver/plan/result/audit:
`/mnt/external/demosaic/benchmarks/mixed16-completed-snapshot-dedup-v4/`.
Result SHA3ccb3964b61996d49ed5df052e3691f697adfb58cf556a7aec975f74f880df0d.
Independent audit SHA8cfa2b38d2bc768d14be5ff8865bb10360af60f3e4daabaedf1fdb0e517e51b5.
Separate audit confirms exactly11 snapshot inodes versus11 disjoint archive
inodes, exact link counts, original stats/hashes unchanged,886 report/metric/
native-PNG hashes and372 active input/source hashes unchanged. Exact live
owner identities rechecked. Both private scripts pass Ruff. No Torch/GPU work.

Free space rises to530.62389GiB. A24GiB review allowance plus1GiB remaining
checkpoint allowance leaves5.62389GiB above the500GiB reserve. This is a
capacity estimate, not a guarantee against other shared-filesystem writes.
Downloader remains stopped. Combined four operations reclaim32.594890594GiB;
existing public storage registry extended and exact independent audit published.
No neural quality result or promotion. Full10k review and later FP32 GPU traces
remain pending; SOTA, decisive real-photo superiority and100MP/10s unmet/unproven.
