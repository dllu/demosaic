# DINO-S completes 10,000; matched cached CPU crops reviewed

The original fresh S arm completed 10,000 updates, whole-checkpoint SHA
`ae74bc17012c85d5253f24da4dbaaec4486ed430aa143d852442754288d56bad`.
AdamW states are at10,000, final LR 1e-5, all 403 logged losses/gradient norms and
all model tensors finite. EMA context-gate L2 is .0315337442. Source bundle 2f1a…
is unchanged. All403 logged observations match completed no-context 10k.
Boundary JSON records the original controller 164667 and B trainer 300610,
resuming from 3,000 with original LR 8.2241071e-5 at 3,001 and a matching prefix
through 3,150. B continues; final immutable model copies remain controller-owned.

Added `scripts/replay_fresh_dino_10k_cpu.py`: CPU FP32 inference only for the new
S arm, reusing the previous four 512px GFX noisy contexts and two serialized
256px exact-GT observations. It checks common training/model fields, original
source bundle, genuine Gaussian initializer and all 403 logged observations.
It archives a private checkpoint snapshot/source and computes no new RAW decode
or noise draw. GFX uses the prior channels-last layout and synthetic cases the
prior contiguous layout. CUDA remains uninitialized.

Actual run `/evaluation/fresh-none-S10k-cached-cpu-v1` completed: four primary
S/reference triplets, four direct none/S rows, two exact-GT triplets and four
unquantized GFX float predictions. Audit verified ten PNG hashes/geometries,
four finite arrays, byte-exact GFX restored rerenders, shared noisy/reference
pixels and direct copied pixels. Synthetic noisy/GT rerenders are exact; new
synthetic restored float arrays were not separately saved. Driver and audit
are archived in the execution directory. All ten new PNGs and two reused
no-context exact-GT triplets were actually viewed before publication.

The models remain close on sky/building/foliage/fence. Fine leaf/bracket detail
is soft; both miss fabric cords and cloud detail. DSCF3880 remains an independent
ISO100/f/5.6 qualitative reference, never exact GT or a scoring target. No
promotion or general DINO benefit is claimed. Published report/JSON and native
images preserve source/ROI/checkpoint/noise/display/license metadata. V43/README
is retained; B and full numerical/native/analytic/full 102MP GFX review remain.

Production package and live frozen workflow files are unchanged. Actual CPU
inference/artifact audit and Ruff validate this script/documentation change;
the existing 488-pass CPU suite remains applicable to production code. Foreign
jobs and source hard drives are untouched; downloader continues independently.
