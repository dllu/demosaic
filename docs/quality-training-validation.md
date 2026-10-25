# V43 quality training: validation evidence

This page records the completed [V93/V94/V95 study](v43-curated-original20k-review.md),
which kept V43's architecture and separated curated membership from the
fine-detail augmentation package. [Current quality work](quality-first-training.md)
uses the newer architectural baseline in [current model choices](current-model.md).
The checks below establish engineering behavior only. Source ranking, final
visual decisions, the production freeze and all six fresh CPU/CUDA preflights
are complete. V93, V94 and V95 completed their 20k stages and independent
saved-state audits. The full matched quality evaluation and all preselected
native views are complete; see the [20k review](v43-curated-original20k-review.md).

## Data, training and reporting checks

Tests preserve old augmentation pixels/RNG exactly, show zero probability
executes no optical kernel, and check continuous low-contrast geometry/means.
Resume rejects changed probabilities/fractions. These are data-path checks,
not evidence of a trained quality gain.

A [discarded CPU training proof](results/v43-quality-CPU-training-proof-v1.json)
also completes 24 actual V43 updates from its exact original EMA and architecture,
covering Commons, native RAW and paired RAW. It executes three photographic
contrast attenuations and one weak-texture sample, with zero optical PSFs;
DINO stays frozen and gradients, optimizer state and EMA remain finite.
This uses batch 1/native 32 before curation and provides no model-quality,
production CUDA, throughput or validation result. The focused data/training
checks pass 53 tests with one skip.

The [matched launcher CPU proof](results/v43-quality-launcher-CPU-proof-v2.json)
then verifies all three arms on explicitly provisional memberships: 24 discarded
updates per arm, 72 in total. All start with the exact original V43 EMA and fresh
optimizers; the 71 model/71 EMA tensors and 69 Adam states are finite. All owners
exit successfully. The data-only comparison preserves all 15 shared paired/native
observations and changes five Commons observations; the fine-detail comparison
preserves all ten paired observations and changes six treatment observations.
Final Python/CPU/CUDA RNG states match across arms. Source archives differ only
in the training manifest for the membership comparison and are identical for
the augmentation comparison. This remains CPU/B1/native32 engineering, with no
quality or timing claim.

`scripts/train_v43_quality_trial.py` prepares the production freeze only from a
completed final curation receipt. It checks that membership and augmentation
are the only recipe differences, and that native/paired/validation manifests
match the original V43 lineage. The launcher runs fresh CPU checks and discarded
CUDA/B16/native256 checks before any of the three 20k stages. It enforces memory,
disk and runtime bounds, keeps caches in authorized storage, retains 4k/8k/12k/16k
diagnostic checkpoints, and uses the fixed 20k final EMA as the primary endpoint.
The training-validation best checkpoint is separate. Failures are preserved;
there is no automatic retry or promotion. The
[production plan](results/v43-quality-curation-and-training-plan-v1.json)
is frozen. Its immutable launch snapshot records the initial memory wait;
the same controller subsequently completed all preflights and started V93.

The [final-cohort preflight receipt](results/v43-quality-final-curated-preflights-v1.json)
covers three CPU/B1/native32 and three CUDA/B16/native256 runs on the actual
39,983/88,484 curated cohorts. Each completes 24 discarded optimizer updates:
144 training forwards and 144 DINO calls in total. Every arm initializes from
the exact original V43 model and frozen DINO hashes with a fresh optimizer.
An independent CPU-only audit verifies all six checkpoint hashes, 71 model/71
EMA finite tensors, 69 finite Adam states with counter24, all metric/input-hash
rows and actual preflight-owner exit. Both phases preserve all 15 shared
paired/native observations for V93/V94 and all ten paired observations for
V94/V95; intended treatment observations change. Frozen source/input guards pass.
The attached production-start observation records V93 live with finite initial
updates. These checks do not evaluate restoration quality.

The [first V93 production diagnostic](results/v43-quality-V93-first-production-checkpoint-v1.json)
also passes independent saved-state checks at step4,000: 71 model/71 EMA finite
tensors, the original restoration tensor keys, 69 finite Adam states with
counter4000, and exact curated/source identities. The retained file matches
`last.pt` at that observation. Scheduled validation completes all 28
condition/CFA cells on eight validation sources, and the same worker continues
beyond step4,000. The older parent omits 19 later configuration defaults; all
shared fields and effective configurations match. An initial raw-dictionary
audit failure and its corrected CPU-only check are preserved. This is a
training diagnostic preceding the completed20k control below. The linked final
20k report now includes full native quality review.

The [completed V93 control](results/v43-quality-V93-completed-training-v1.json)
now records 20,000 optimizer/training forwards, 160 validation forwards and
20,160 DINO calls. Its original worker exited successfully. The independent
CPU-only auditor checks all four diagnostic files plus final and validation-best
checkpoints: original lineage/effective architecture, finite model/EMA/Adam
states, correct counters, exact curated/native/paired/validation/protocol hashes,
and frozen inputs. All 801 scheduled training rows are finite; all five
validations cover the same 28 condition/CFA cells on eight sources. Its first24
production inputs exactly match the discarded CUDA probe. Validation-best is
step20,000 in this run; final20k EMA remains the predefined primary endpoint.
V94 completion is checked below. These are training/artifact checks;
restoration quality still requires the complete matched evaluation and native
crop review.

The [completed V94 larger-data control](results/v43-quality-V94-completed-training-v1.json)
passes the same complete saved-state audit: 20k updates, 20,160 DINO calls,
all retained states and five scheduled validations. Its validation-best is at
12k; final20k EMA remains primary. Across all 801 logged batches, the V93/V94
control audit preserves 390 shared native/paired observations and changes 411
Commons observations. This verifies the intended data comparison rather than
restoration quality.

`scripts/audit_v43_quality_training.py` replays these saved-state checks for each
completed arm with CUDA hidden. Each receipt retains the executed audit source.

The [CPU reporting integration](results/v43-quality-reporting-CPU-proof-v4.json)
also passes using the original V43 and three actual discarded 24-update EMAs:
48 genuine neural/DINO forwards, 84 metric rows, and eight native 160-pixel
triplets from two held-out photographs. All 24 panels were actually viewed.
The noisy/GT pixels match exactly across methods, as do the display settings;
independent summary arithmetic has zero discrepancy. Weights, configuration,
parameter identities, RNG and declared inputs stay unchanged. This small
CPU/native176/B1, two-condition/two-CFA check supplies no quality gain, production
CUDA or full-panel qualification. Earlier probe output-path/metadata-format
failures and their outputs are preserved in the receipt. Full evaluation still
uses all 427 photos, seven conditions, four CFAs and native256.

The [CPU validation/checkpoint-boundary proof](results/v43-quality-validation-CPU-proof-v1.json)
adds 24 genuine V43 training and 120 validation forwards, with 144 DINO calls.
It uses the unchanged planned 20k schedule, stops at 24 and tests diagnostic
validation at 12/24 on two sources across all seven conditions/four CFAs.
All 71 model tensors, 71 EMA tensors, 69 Adam states, RNG states and 24 actual
input/metric records match the no-validation CPU witness exactly (elapsed time
is excluded). Retained 12/24 checkpoints have the right optimizer counters;
the repeated final boundary save is byte-identical. The launcher now accepts
that identical repeat while rejecting changed bytes at an existing boundary.
This is discarded CPU/native32/B1 engineering on provisional membership. It
does not change the production validation cadence or establish model quality.

## External artifact preparation

The [preparation-only storage check](results/v43-quality-external-artifact-preparation-v1.json)
verifies a fresh external namespace/owner marker, frozen input/code guards and
all three run-path mappings. It prepares CPU-only provisional configurations;
no controller, checkpoints, CUDA or production training were launched.
`--artifact-root` puts run artifacts under a fresh `/mnt/external/demosaic`
directory, retaining plans/code locally and fixing free-space reserves at
64 GiB on the system disk and 384 GiB externally before the production freeze.
The default local-artifact policy remains 64/500 GiB. The source scanner completed
under its original 500 GiB floor before production preparation.

V95 later stops at a resource guard around logged step1,025, before its first
saved training checkpoint. The old guard lacks the actual readings, so its
trigger cannot be identified retrospectively. Low system-disk space blocks the
initial recovery. The original status/logs and all 62 failed-trial
files are preserved with byte hashes and a path mapping. The
[cold-checkpoint relocation](results/cold-checkpoint-relocation-20261021-v1.json)
moves 66 owned old experiment inodes/116 path aliases to the external SSD,
reclaiming about 32.4 GiB. Original checkpoint bytes, logical paths, modes and
mtimes remain available; current study inputs, source code, photos and historical
receipts stay unchanged. Current frozen source/input guards pass afterward.

`scripts/recover_v43_quality_trial.py` prepares this explicit early-V95 recovery
only after verifying the terminal owner identities, completed controls and
preflights, matched control inputs, and restored resources. It archives the
unsaved failed trial, then runs the exact original frozen worker/configuration
from the original V43 initializer for a fresh20k stage. It keeps the resource
and runtime bounds and single-attempt claims. The completed V93/V94 stages are
reused. Final status still requires the full three-arm observation audit and
will retain the recovery provenance.

The [actual recovery observation](results/v43-quality-V95-manual-recovery-v1.json)
confirms that first recovery continued beyond the archived prefix. All 42 scheduled
recorded batch fingerprints through step1,025 match exactly; the recorded new
losses and gradients are finite. This checks logged inputs, rather than claiming
bitwise equality of unlogged steps or floating-point training states.

That worker subsequently stops at the same generic guard near step1,550,
again without the resource readings needed to identify the trigger. Both
unsaved trials and controller evidence remain archived. The current recovery
logs exact RAM/free-space/mount readings every2s, includes them in failures,
and suspends its owned process group for disk-only shortages. It resumes the
same PID after original launch thresholds are stable60s; RAM below24 GiB still
terminates it. Numerical worker/configuration and resource thresholds are
unchanged, and the original wall-time bound includes suspension. Process-group
ownership, parent/child suspension/continuation and stopped-group cleanup pass
an actual CPU integration test. A controlled3s pause on the actual V95 CUDA
worker also preserves its identity and continues with finite recorded training.
These checks establish operational continuation, rather than floating-point
state parity or trained image quality.
The [current recovery receipt](results/v43-quality-V95-resource-telemetry-recovery-v2.json)
records the causal clarification, exact readings, CPU/CUDA continuation checks
and exact replay of all 63 logged batches through step1,550.

The later [actual reserve event](results/v43-quality-V95-actual-disk-pause-v1.json)
records root free space below 64 GiB after 8k validation, with RAM above its
active floor. The worker and all nine observed descendants are stopped at
logged step 8,025. Another 71 closed checkpoint inodes/71 aliases move to the
external SSD after full copy-hash verification, reclaiming 32.4 GiB locally;
all original aliases resolve to targets with preserved modes/mtimes. The
controller resumes the same worker after 60 seconds of qualifying readings and
frozen-input checks. Its paused metric bytes remain an exact prefix, and
recorded losses/gradients stay finite through step 8,300 in the snapshot.
This qualifies actual reserve-triggered continuation, without proving bitwise
learned-state parity or image quality. The original two guard causes remain
unknown; their older snapshots are not rewritten.

V95 subsequently completes all 20,000 updates under that same worker identity.
Its [independent final audit](results/v43-quality-V95-completed-training-v1.json)
checks all six retained checkpoint files, 71 finite model/EMA tensors and 69
Adam states per file, correct steps, canonical V43 architecture, unchanged
manifests, all 801 logged training rows and the first 24 exact CUDA-probe inputs.
The five scheduled validations contain all 28 condition/CFA cells, eight sources
per cell. Counts are 20,000 training forwards, 160 validation forwards, 20,160
DINO calls and 20,000 optimizer steps. The training worker/controller exit;
the completed study also verifies 390 matched paired/native control rows and
197 matched paired rows for the fine-detail treatment. These saved-state and
trace checks do not establish held-out image quality.

## Evaluation launcher integration

The [CPU evaluation-launcher check](results/v43-quality-evaluation-launcher-CPU-proof-v3.json)
passes on original V43 plus the same three discarded 24-update EMAs. The new
controller/worker complete 48 real neural/DINO forwards, 84 metric records and
eight native 160-pixel triplets; all 24 panels were actually viewed. All metric
records and PNGs match the earlier reporting witness byte for byte. Native
metadata matches except for report-specific checkpoint snapshot paths.
The common noisy/GT pixels match across methods, independent summary arithmetic
has zero discrepancy, and weights, DINO, configuration, parameter identities,
RNG and declared inputs remain unchanged. Sampled physical-input hashes match
before/after forwarding and across methods. All owners exit; CUDA remains off.

A prepared v1 was unused. V2 stopped before any model forward because a strict
configuration comparison distinguished lists from tuples; the canonical JSON
comparison now matches the established training check. The failed artifact/log
and owners' exit are preserved before a fresh v3 freeze. These checks cover the
small CPU photo branch only. They do not qualify the other production branches;
the later completed production checks are recorded below.

The generic native-pixel validator also passes on 64 retained triplets from
existing real, carrier/flat, color-grid and GFX reports. It verifies PNG hashes,
native160 rectangles and shared noisy/reference pixels across methods without
importing torch or running inference. This checks report-schema handling, not
new branch execution or another visual review.

Before production evaluation, its controller now records exact resource
readings and uses the same owned-process suspension helpers as V95 recovery.
Disk-only shortages pause the existing worker; continuation requires stable
launch headroom and a fresh frozen-input check. RAM breaches terminate it, and
the original wait/stage bounds remain. Three
[actual CPU worker tests](results/v43-quality-evaluation-resource-control-CPU-v1.json)
with controlled resource readings pass: same-PID continuation, changed-input
rejection while suspended, and RAM-floor failure with its exact reading.
The numerical worker and native-validator syntax trees are unchanged. This is
resource-control evidence, without new inference or production-quality evidence.

## Completed production evaluation

The [seven-stage result](results/v43-curated-original20k-complete-review-v1.json)
binds the original V43 and all three final 20k EMAs. Actual joint-model/DINO
calls total 17,824. Model/DINO/configuration/parameter-identity/RNG checks pass
per stage, and sampled physical-input hashes match before/after and across
the four checkpoints. All workers and the controller exit.

Primary coverage/arithmetic checks include all 111,636 photo/procedural rows,
648 known-camera rows and 810 unseen-camera rows, each with nine methods.
Maximum independent summary discrepancy is 7.11e-15. The analytic auditor
separately checks all 2,240 carrier/flat rows, 140 groups and 3,760 scalar fields,
with maximum discrepancy 2.23e-16. These scalar checks do not recompute model
predictions or assign training-seed uncertainty.

The saved-color auditor checks all 1,176 observations/4,704 float predictions,
28,224 Torch64 scalar fields and exact rerendering of all 12 native triplets.
Maximum scalar discrepancy is 5.56e-16. A separate descriptive-summary audit
checks all 72 groups/864 fields, with maximum discrepancy 8.68e-19.

All 96 source triplets are represented in actual native views: 132 distinct
160-pixel panels after shared noisy/reference cells. PNG/source/ROI/conditioning/
display metadata and common pixels match across methods. The GFX scene and two
highlight contexts remain separately captured qualitative references, with no
pixelwise scores or full-frame output. The report retains real quality tradeoffs;
passing execution/arithmetic checks does not promote V95 or establish SOTA.
