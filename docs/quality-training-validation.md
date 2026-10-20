# V43 quality training: validation evidence

The [quality study](quality-first-training.md) keeps V43's architecture and
separates curated membership from the fine-detail augmentation package.
The checks below establish engineering behavior only. No new production model,
quality improvement or speed result is claimed. Production still requires
completed source ranking, final visual decisions and fresh CPU/CUDA preflights.

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
there is no automatic retry or promotion. **The production plan is not yet
frozen or launched**, because full source ranking and final review are pending.

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
The default local-artifact policy remains 64/500 GiB. The live source scanner's
original 500 GiB floor is unchanged; its completion precedes production work.

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
small CPU photo branch only. Full photo/real/texture/color/GFX execution, final
curation, production CUDA and model quality remain unproven.

The generic native-pixel validator also passes on 64 retained triplets from
existing real, carrier/flat, color-grid and GFX reports. It verifies PNG hashes,
native160 rectangles and shared noisy/reference pixels across methods without
importing torch or running inference. This checks report-schema handling, not
new branch execution or another visual review.
