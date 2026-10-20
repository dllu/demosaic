# V92 full quality and native review preparation

V92 remains in its original4000-step training run. This preparation does not
establish a quality gain. The [fixed head-only protocol](late-rgb-head-only-v92.md)
and [training engineering checks](late-rgb-head-only-engineering.md) remain the
source of its scope and criteria. Completed V90 is a historical exploratory
reference chosen after observing its results, not a newly randomized arm.

The [frozen review plan](results/late-rgb-head-only-review-plan-v1.json)
copies all47 actual V92 training modules. Every neural quality prediction is
fresh FP32: historical V90 original4000, V92 original4000 and V63 parent. Reuse
is limited to the established V43/RawNIND scores and exact source/reference
PNGs, with the unchanged source/protocol/coverage/classical-control witnesses.
Both completed endpoints must pass independent state/source/data/horizon/RNG
checks before any new quality inference.

## Fixed coverage and criteria

The same ten stages cover boundary, known4, unseen5, full427 photos plus16
procedural sources, primary statistics,418/416-source sensitivities, GFX,
analytic detail/ADC, hue and supplementary highlights. There are six methods
in each primary panel:432 known rows,540 unseen rows and74,424 photo/procedural
rows. The unchanged analytic panel retains all192 original ADC draw/layout
slots and12 group means; deterministic ADC draw labels are not independent
observations. Hue retains all1,176 observations per neural checkpoint.

V92's primary criteria apply to V92 versus V63: at least+.05dB with positive
lower95% source-bootstrap bounds on photo, known and unseen means, with photo
SSIM loss at most.0001 and complete actual native review. A failed historical
V90 gate does not veto V92, and historical success cannot compensate for V92
failure. V92−V90 effects and intervals are reported as historical contrasts.
The weak-detail claim separately retains the two+.05 carrier-gain requirements,
flat RMS cap and every individual ADC loss limit from the frozen protocol.
There is no automatic promotion, training extension or SOTA claim.

Native packaging retains all eight boards/81 source triplets/125 cells. The
report package includes two unchanged160px noisy/restored/exact-GT photo
triplets per endpoint and all four standing GFX regions: sky, building,
foliage and chain-link fence. The ISO100 DSCF3880 rendering remains an
independent qualitative reference, not GT or a scoring target. Coordinates,
display transforms, noise metadata, source identity and checkpoint hashes
must match across methods. Every cell still requires actual viewing before
quality interpretation. In primary/analytic boards, indexed labels
`0:control` and `1:control` identify V90 and V92 respectively; checkpoint hashes
determine identity. The crop section and GFX/hue/highlight panels use explicit
V90/V92 labels, including distinct highlight captions for identical run names.

## Actual preflight evidence

All63 focused reader/criterion tests pass, plus19 native-board tests. Negative
cases reject incomplete/live training, discarded engineering states in every
quality stage and packaging, camera/SSIM failures hidden by historical success,
and individual ADC failures hidden by group averages. Byte checks distinguish
signed zeros.

The [CPU integration certificate](results/late-rgb-head-only-review-CPU-preflight-v1.json)
independently reads the genuine completed CPU/CUDA16 states and their historical
global references. Both retain115 model/115 EMA/24 candidate AdamW states,
exact common V63 bytes, identical observations and final RNG. The production
reader rejects the actual still-running full trainer. Existing V90/V91
metrics keep their original model identities while replaying the new role-based
criteria; all192 ADC cases,12 means and322 original LR rows agree. The native
packager verifies all125 cells and reproduces all20 historical PNGs exactly.
It does not assert a new manual view or produce a V92 prediction.

Preflight v1 was frozen but never executed: review found that its proposed
output lay outside the frozen package's allowed subtree. V2 places outputs
inside its own `work/` directory and is the source-frozen, actually executed
certificate above. The earlier development reader and unexecuted freeze are
preserved; no failed training or quality inference was retried.

The independent [retained first1000 state audit](results/late-rgb-head-only-first1k-state-v1.json)
also passes. All91 common model and91 common EMA tensors remain byte-identical
to V63, all115/115/24 states are finite, and every head AdamW counter is1000.
The output and all four prompt projections have learned nonzero weights.
All56 recorded source/forward/loss observations through1000 match original
V90; unlogged observations are not separately replayed. These are engineering
checks on a retained state, not early quality selection or a new endpoint.

## Owned serial queue and storage

The [queue receipt](results/late-rgb-head-only-review-queue-v1.json) binds the
exact live training controller and the source-frozen review. Review controller
1278489/create1792506281.09 waits for successful completion and actual exit of
training controller1265645 and worker1265932. CPU closure1278491 follows all ten
review stages; retained-reference preparation1278492 follows closure. CPU
package watcher1279000/create1792506310.08 waits for all three exact owners to
exit before using the [frozen package plan](results/late-rgb-head-only-review-package-plan-v1.json).
Every owner was verified live by PID/create time in the
[handoff receipt](results/late-rgb-head-only-review-handoff-v1.json).

Artifacts use the local SSD under
`.cache/benchmarks/late-rgb-head-only-v92-original4k-review-v1/`, with outputs
inside its frozen `work/`. This preserves the external500GiB reserve while
training retains checkpoints. The root64GiB reserve remains explicit; over72GiB
was required before preparation, against an estimated under8GiB of equivalent
review artifacts. Legacy reviews retain their original128GiB output-volume
default. No previous checkpoint, raw original or other project's process was
changed or deleted. The actual cached GFX pair and prepared evaluation inputs
avoid reading the source hard drives.

Operational files are `status.json`, `closure-status.json`,
`report-assets-status.json` and `queue-launch.json` in that cache directory.
The exact training status remains in
`/mnt/external/demosaic/experiments/late-rgb-head-only-v92-original4k-v1/status.json`.
Failed stages preserve evidence and receive no automatic retry. Complete
original4000 training, full inference, actual native viewing and the final
quality decision remain pending. The working model and README stay V43.
