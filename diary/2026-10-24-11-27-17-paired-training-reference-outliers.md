# Audit paired training references for isolated outliers

Recorded: 2026-10-24T11:27:17-07:00 (America/Los_Angeles).

Previous goal turn was progress: e23dce5 traced the large museum deficit to one
outlier, completed both camera repair panels, corrected the reference-supported
detail interpretation using cross-scene coordinates, and recorded V114's
completed 20k endpoint. At this turn's initial 11:21:54 PDT check, the original
training owner 867877/1792848017.25 was live on V115 step 600 with eight
descendants. Evaluator 986158/1792855221.87 and independent reviewer
986159/1792855223.35 were live, waiting with no children or completed stages.
No owner, fixed budget, observation, active recipe or queued source is changed.

The development-reference findings raise a training-data question, but the
original paired train32 cohort uses different cameras: Sony ILCE-7C, Nikon Z6,
Canon EOS 6D and Nikon D40. Added `scripts/audit_paired_outliers.py` to inspect
only training/quarantine cached references, preserving all original arrays.
It requires actual same-channel support at all nine reference samples, avoiding
the earlier erroneous assumption that input and registered reference CFA phases
match. Eight same-phase neighbors, ratio 2/minimum excess .005 and sigma 6 from
the noisy input supply a conservative isolation screen, not a calibrated
reference-noise model or proven defect detector. The separate existing input
repair includes its own coherent-light filter. No automatic masking/admission
or learned scoring is added to the diagnostic.

Frozen source and a declared full scan execute on all 64 captures / 576 native
512 crops. The scan exits 0 with unchanged source, manifest and all crop hashes.
It reads SSD caches only, without RAW decoding, noise generation, model/encoder
calls, optimizer updates or CUDA initialization. There are 777 reference
isolation candidates across 63 crops / 21 scene IDs: 767 valid and 10 already
masked. Valid candidates are 4.19 per million cached valid measured samples,
including repeated observations. This is not a unique-defect rate or training
draw probability. Camera candidate counts are 444 Sony, 58 Z6, 145 Canon and
130 D40; only D40 has the ten preexisting masked candidates. Existing input
repair flags 742 sites; 47 input/reference candidate locations coincide.

The first independent audit attempted unavailable SciPy and failed at import
before reading any input. Preserve its source/log and zero-work failure receipt.
A fresh NumPy-only v2 uses independent strided 3×3 phase-plane windows, sorted
eight-neighbor values and nine-site support, comparing every candidate mask bit
with the frozen direct-offset implementation. All 576 crops, original mask
memberships and selected extrema agree exactly. No dependency is installed into
the active training environment. All failures and successful source versions
remain distinct.

Selected up to two distinct scenes per camera by the largest valid candidate
count, then the largest valid point excess, before viewing. Seven native
noisy-Malvar/approximate-AHD pairs were actually viewed at original resolution:
Kortlek, Metalldel, wet_charred_wood, helmet, Iain01, bananapi and couch. They
contain printed dots, reflective/wet surfaces, specks and textile structure;
some references also retain grain, moire or AHD artifacts. These contexts do
not prove every isolated point is defective, and blanket withholding/masking
would discard useful fine-detail content. The 14 unchanged native 160px cells
use common +2EV/WB/matrix and accurately labeled nonexact RGB references.

Independent recurrence grouping only accepts unambiguous reference coordinates
when all contributing registration offsets agree. One red coordinate,
Nikon Z6 [2794,3466], recurs in sewingmachine and bananapi. The follow-up inverts
registration for all six cached Z6 captures/three distinct low-ISO references,
including odd shifts, and queries both reference-space and physical input
coordinates separately. Two input captures sharing a reference are not treated
as independent reference evidence. The same bright red speck is visible in all
six noisy captures across three unrelated scenes. Lower-ISO input value/local
median is .45746/.02346, .54625/.00989 and .31707/.00664; the higher-ISO input
values all reach the same stored 1.07495. Low-ISO reference value/local median
before alignment gain is .12291/.04873 sewingmachine, .02014/.01730 couch,
.07551/.01528 bananapi. The couch reference is near background and is retained.
Six further native cells across these three scenes were actually viewed.
The fixed coordinate and visible speck support a capture/sensor artifact; no
physical mechanism or sensor serial identity is proven. The high-input-noise
screen misses one rescaled sewingmachine observation, showing why detection
counts are not a complete defect inventory.

Prepared a separate opt-in reference-mask revision for the two reviewed
reference SHA256s only. Four registered crops exclude a 17×17 neighborhood around
the mapped point, removing 1,156 previously valid measured samples. This also
excludes intersecting coarse AHD loss blocks. Radius 8 is a conservative small
training exclusion, not an exact bound on AHD influence; no estimated clean
intensity is substituted. Every other 572 crop path/hash and all noisy inputs,
RGB/measured targets, counts, scene/capture identities, CFA/WB/matrix and noise
conditioning remain exact. Three previously accepted isolation candidates lie
inside the reviewed neighborhoods; the other 764 remain eligible. No whole
photograph is removed. Current recipes keep the original paired manifest.

Independent verification rebuilds all four masks from sensor coordinates and
registration, checks all 576 case/crop records, and calls the real native256
PairedDataset on fourteen indices. Ten baseline samples preserve ordinary
behavior; four precomputed indices 1211, 7875, 13230 and 54081 fully cover the
four exclusions. All nonmask tensors match exactly, transformed masks agree
with independent NumPy rotation/flip, and all four selected masks lose exactly
289 samples. On an artificial output perturbation, the actual paired objective
has zero gradient at excluded samples, including coarse RGB supervision, while
the original objective has nonzero response. This is plumbing validation,
not a model prediction or trained-quality result. Torch RNG remains unchanged
and module forwards are prohibited. The reader/audit exits 0.

Ten new tests cover shifted reference phases, missing support, coherent lines,
an independent scalar oracle, invalid thresholds, existing-mask/coarse-block
accounting and held-out split rejection. Together with original isolated and
cluster repair tests, all 37 focused tests pass in .18s; Ruff passes after
formatting. The first lint check identified only dictionary-literal style in
the new tests, corrected before freezing/execution. No model/training tests are
repeated for this CPU-only diagnostic and dataset revision.

Published [current data review](../docs/paired-reference-quality.md),
[machine receipt](../docs/results/paired-training-reference-outliers-v1.json),
three native boards with 20 actually viewed/verified cells, and links from the
data, admission, camera, experiment, requirements and current training docs.
Refreshed remaining current-data/requirements status text from V114-running to
V114-completed / V115-running. Existing receipt bytes and historical entries
remain unchanged. The new data revision is ready for a future quality trial;
it has no trained-benefit claim and does not establish the cause of global
fine-detail loss.

Plans, complete scan, independent checks, preserved import failure, original
native reviews, reviewed-source decision, revised arrays/manifest, actual
reader/loss audit and publication sources/logs are under
`.cache/current-quality-20261023-v1/paired-reference-outliers-v1/`.
The revised manifest is `work/cleaned-train32-v1/manifest.json` there; original
unmodified files are referenced by absolute path, avoiding a full corpus copy.
Public provenance binds the source identities, exclusions and retained artifacts.
Total learned inference, optimizer updates, new noise observations and RAW
decodes for this entire turn are zero.

At 11:44:43 PDT, all three original GPU-chain owners remain live with exact
creation times. V115's latest log is step 2150; both reviewers still have zero
children/completed stages. Available RAM is 73.81 GiB, internal free 795.38 GiB
and external free 254.08 GiB. New reviewed files stay internal. The evaluation's
original 248 GiB first-stage / 216 GiB phase-start / 208 GiB runtime thresholds
remain unchanged. No process is restarted or learned budget increased.

This advances the requested clean-data pipeline while preserving fine-detail
examples. Broad real-camera superiority, faint high-noise detail and 100MP/10s
remain unmet or unproven. Let the original V115/evaluation/review chain finish,
then use its actual quality evidence to choose the architectural parent for
the next trained detail/data comparison. The full PROMPT.md goal stays active.

Final verification at 11:46:53 PDT passes 781 unique file bindings, all current
frozen training/review plans, byte equality for all 16 nonmask array fields in
the four revised files, all 20 native160 cells and 138 local Markdown links.
No existing machine receipt or library/configuration/instruction file changed.
All three exact owners are still live; V115 is at logged step 2300 and both
reviewers are waiting with no children/completed stages. Preserve the final
verification source, result and log locally. Staged whitespace is checked before
commit/push.
