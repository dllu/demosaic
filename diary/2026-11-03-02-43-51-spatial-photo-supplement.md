# Compare spatial attention on retained irregular dark photos

Recorded: 2026-11-03T02:43:51-08:00 (America/Los_Angeles).

The previous goal turn made concrete progress: committed/pushed `cb50813`,
completed all four genuine CPU/CUDA16+2 checks and the independent state audit,
then launched the original V144/V1451000-update training and fixed reviews.
This turn verified controller PIDs2070050/2071171 and the original V144 worker
PID2120154 against their creation times and live process commands. V144 continues
without restart; observed progress includes650, with finite logged gradients.

The earlier phase validation's64 photographic observations are useful precisely
because the optional correction left them unchanged. However, their eight-source
cohort is mostly architecture/devices, with one bird image. Added a separately
bound photographic supplement: retain those64 native512 observations and add64
native384 observations from eight organic sources. The first metadata-only search
at native512 found no new keyword-matched organic examples. Before any new noise
or inference, I examined13 eligible native384 source crops and selected indices
0,2,4,5,8,9,11,12: feathers, wet leaves, moth scales, grass/bark, apple skin,
butterfly, heron feathers and moth hairs. The first preview attempt used relative
cache paths from the repository and failed; resolving against the manifest's
directory fixed source reading. No source file was changed.

All16 source IDs are validation-only and absent from both photographic training
ID sets. Their original bin8uint16 cache hashes match. No resizing: new center384
contexts, center160 ROI[112,112,160,160]. Keep the previous512 contexts and
ROI[176,176,160,160]. Each source has faint mean.02/contrast.125 and dark
mean.003/full-contrast variants, all four CFAs. Noise matches the existing
ISO6400 prior, with16-bit ADC/black.03 and a new source-keyed seed2026110301.
Only64 new noisy observations are generated; the previous64 stay byte-bound.

Independent pre-inference checks validate all128 input fingerprints, reconstruct
the clean RGB targets from the original bin8 pixels to1.1155930165762662e−8,
and check the ADC lattice within.0005035594103901531 code. These constructed
targets are exact for the simulation, not physical-scene GT. Standalone metadata
and source-only selection are frozen before parent/candidate output inspection.

Created `review_spatial_photo_supplement.py` and its independent auditor, with
three meaningful metric fixtures (gain/DC separation and error decomposition at
384/512, flat-target rejection). Ten relevant metric/flat/analysis tests pass;
Ruff passes. Source-frozen root:
`.cache/quality-20261103/V144-V145-photo-supplement-v1/`.
Its controller PID2125778 preserves the original primary jobs. The supplement
declares64 new V143 parent calls and128 each for V144/V145, while reusing64 old
V143 predictions:320 root and320 encoder forwards. Endpoint collection waits
for both original primary reviews and their exact owner exit. Original training
and150-input review budgets are unchanged. No source-drive/RAW/dataz access.

All64 new V143 forwards completed, with exact weights and unchanged RNG. A
separate baseline-only reporter uses these and the64 retained predictions,
without candidate placeholders or new inference. Baseline mean native DCT16
luma response is.15070/.39895 for faint/dark organic cases (ideal1), versus
.29856/.53145 for the retained photo cohort. Full-context camera-RGB error is
37.46906/33.68580 DN16 on the organic cases. These are32 cases per condition
from eight sources; neither128 independent photos nor a causal cohort comparison.

Viewed all24 new native160 noisy/V143/constructed-GT triplets in four unresized
sheets. Broad shapes survive, but feather, moth and bark/grass detail is largely
lost; blurred islands and false color remain. Shared faint contrast8 views make
that gap conspicuous and heavily clip the noisy panel. The first independent
baseline auditor expected a redundant image-level exposure field; the baseline
assets declare it inside their observation. Preserved the original reader and
report, then wrote a separate v2 reader using that declared observation value.
All128 metric rows and5,529,600 PNG panel RGB channels pass independent NumPy64
checks. Largest metric difference3.0965452424425166e−11. No predictions, PNGs,
noise, report bytes or parent forwards were replaced/repeated.

Published all24 PNGs, byte-preserved source/input/collection/baseline/audit
receipts and the recovery record. Updated README's representative crops with
faint feathers and dark grass, retaining one periodic exact-GT example and both
standing real-scene comparisons. Full source author/license metadata accompanies
each image. [Report](../docs/spatial-photo-supplement.md) and the publication
receipt preserve the remaining evidence. No improved-model claim: V144/V145
training and their original/supplemental comparisons remain in progress.

V144 subsequently completes its full1,000 updates,16,000 training targets and64
validation forwards (1,064 root/DINO calls). Final checkpoint SHA256
`b39976396d90c096cb52157d208b172c86148f84dfa044d908f0899d08973e85`.
Its preserved endpoint has91 model/EMA tensors and89 finite Adam states. The
original primary collector completes102 forwards, then its metric/pixel audit
passes. Remaining flat/faint/JPEG stages follow. The same original training
controller launches fresh V145 from V143; no run was restarted or extended.

The original primary review subsequently stops after all V144 stages succeeded.
The controller's completion bookkeeping expected `independent-audit-v1.json`
inside the flat directory, while the real auditor writes
`independent-flat-audit-v1.json`. All102 primary and48 flat predictions, both
numeric/pixel audits, faint analysis/audit, four JPEG boards and the V143 flat
comparison were already complete. The supplement correctly stopped on that
failed dependency. Both original owners were verified absent; original status,
logs, sources and plans remain unchanged.

Corrected the public receipt path and added explicit adoption/recovery support.
Four tests check no-model adoption and rejection of changed counts, model state
or RNG evidence; a51-case metric/flat/review run passes. Primary recovery plan
`V144-V145-review-v1/review-recovery-plan-v2.json` adopts all150 V144 outputs and
prepares V145 once. New primary owner: PID2130928, creation1793704958.37.
Supplement recovery plan
`V144-V145-photo-supplement-v1/supplement-recovery-plan-v2.json` adopts the64
existing V143 outputs and follows that exact replacement primary owner/plan.
New supplement owner: PID2131402, creation1793705072.97. Both replacement owners
were verified live and waiting; V145's original training had reached325.
No model/noise replay, training restart or scope/budget reset occurred. Recovery
uses conservative absolute deadlines derived from the original owner creation
times. Separate `*-recovery-status-v2.json` files preserve the original failures.
All eight failure/recovery receipts/logs are copied byte-for-byte into docs;
[recovery publication](../docs/results/spatial-photo-review-recovery-publication-v2.json)
records the original and published hashes. Original64-parent/128+128-candidate
supplement counts and both original150-input reviews stay unchanged.
