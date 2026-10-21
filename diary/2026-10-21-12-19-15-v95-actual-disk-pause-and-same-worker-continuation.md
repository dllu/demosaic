# Continue V95 after an observed disk-reserve pause

Recorded: 2026-10-21T12:19:15-07:00 (America/Los_Angeles).

V95 completes validation and saves its 8k diagnostic checkpoint. A real
root-disk reserve breach then stops its owned process group at logged step
8,025. Exact readings capture root free space below 64 GiB, with RAM above the
24 GiB active floor and external reserve/mount identity intact. The worker
PID3422418/create1792605984.94 and all nine observed descendants are stopped.
This identifies this event's trigger; the two earlier generic guard failures
remain causally unknown.

Inventory the remaining closed project checkpoint artifacts. Exclude all
current frozen inputs, protected inodes and open/mapped project files; require
owned regular files, complete hardlink alias enumeration and stable metadata.
Select 71 old experiment/benchmark inodes with 71 aliases, representing
32.3718 GiB allocated. Hash them before copying, verify each entire external
copy, preserve modes/nanosecond mtimes, then replace original aliases atomically
with links to verified targets. Reuse the prior relocation operator in a fresh
namespace. Originals, datasets, current training inputs and other workloads
remain untouched. Frozen training guards pass before and after the relocation.

The new archive is
`/mnt/external/demosaic/cold-project-checkpoints-20261021-v2/`; its local receipt
is `.cache/quality-first-20261020/cold-checkpoint-relocation-v2/receipt.json`,
SHA `4a6900c27f4aa77ec87c7358628e4e8522187298682aa894ba69285b8876ff8a`.
Root free space returns to about 90 GiB; external free space remains about
427.5 GiB, above the unchanged 384 GiB reserve. All original aliases and target
metadata also pass the subsequent independent path/metadata check.

The controller continues the same V95 worker after 60.013 seconds of qualifying
resource samples and fresh frozen-input checks. The observed pause lasts about
279 seconds. The paused metric bytes are recovered and verified as an exact
prefix of the continued log; the immutable snapshot reaches step 8,300 with
finite recorded losses and gradients. Both 4k/8k validations and diagnostic
checkpoints remain present. No numerical worker, configuration, data, resource
threshold or training identity changes, and no training restart occurs.

The [published reserve-event evidence](../docs/results/v43-quality-V95-actual-disk-pause-v1.json)
links immutable paused/resumed status, metrics prefixes, resource samples and
relocation receipts. Detailed proof SHA:
`ed1496f6ed603244f8248be529f790c705a305a1fd182c2135e38a3efb88d290`.
This is actual process continuation evidence, not bitwise learned-state parity
or performance evidence. V95 still needs 20k, then full matched quality
evaluation and native crop review. V43 remains the working reference and
speed work stays deferred.

