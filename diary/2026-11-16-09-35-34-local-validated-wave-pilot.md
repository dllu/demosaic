# Input-only local conditional wave pilot and full-panel evaluation

Recorded: 2026-11-16T09:35:34-08:00 (America/Los_Angeles).

The preceding goal turn was progress: fixed additional-wave GT oracle fits,
audits and native evidence were published as5f4faf6c. This turn moved from
target-assisted gains to an input-only reconstruction component. V132's exact
worker224010/create1794843486.14 and endpoint reviewer178183/create1794842394.64
were verified live before work. Neither training process is signalled/restarted.

Implemented `demosaic.local_validated_waves`: native256 discovery windows,
stride128, local129 validation/stride32. Half of each CFA phase forms A/B.
Each A-only fit refines the step geometry and first frequency, then discovers
a competing angular family after removing the first fit. Weighted color
coefficients and noise proxies use discovery samples only. Direction/color
validation compares with a fixed A-only conditional null containing the other
direction; frequencies must match across folds within1.5 native bins. Fixed
soft support at thresholds0/2/4 is computed globally or locally from identical
candidates. Only then is the parent's wave projection replaced, avoiding
doubling a component already present. Smooth overlap blending localizes changes.
Scores are empirical; no formal false-detail/risk claim is made.

The complete24-input fixed pilot includes12 procedural role images from the
first two geometries/near/far400/RGGB/repeat0, ordinary bark/fur, four ADC-only
material controls and all six protected real contexts/profiles. Prediction
closes all24 before loading targets/references;196 patch pairs,126.684s CPU,
zero new model/DINO/source/noise/RAW/optimizer work. All four zero-noise controls
are bit identity across all six variants.

I caught and corrected a baseline-label mistake before publication: the finite-
wire caches use V143, SHA96d146d0..., not V120. Their three authoritative original
plans all bind that checkpoint. Photographic/GFX cached parents are V120,
SHAa9d9b6b4.... The initial pilot/full-panel model metadata and finite score/plot
labels incorrectly said V120. All original bytes are preserved. Label-only
lineage addenda, corrected configuration91a729a6..., metrics, figures and audits
retain exactly the same numerical inputs/outputs/crop cells. Future preparation
checks the actual wire checkpoint; two tests reject a mislabeled V120 parent.
The user-facing progress correction explicitly identifies V143. No numerical
producer is restarted. A separate exact-controller watcher will derive corrected
V143 labels/scope after the frozen full-panel scorer finishes, preserving its
original receipts too.

At fixed threshold2, far weak response V1430.95794% → global2.31517% →
local2.80121%; strong33.78291% →42.31157% →43.33239%. Quiet RMS
4.00857→4.08421→4.02596DN16. Local's quiet cost is+0.434% versus parent,
compared with global+1.887%. Weak-increment RMS11.78863→11.84905→11.80386
(local still+0.129% versus parent). Source1 drives the gain:0.9018%→4.5916%;
source0 effectively unchanged1.0141%→1.0108%. Near weak response barely changes;
local/global quiet costs remain positive. These two-geometry means are not
comparable to the prior eight-source V200/oracle aggregates.

Ordinary bark/fur local sRGB PSNR changes are+0.000324/+0.001032dB, visually
near V120. All28 primary native boards/14 triplets were inspected. Independent
NumPy audit reproduces679 metric fields and9,216,000 RGB channels exactly;
PSNR/finite-increment error is zero, largest band-scalar discrepancy2.50e−15.
The corrected report retains every crop-cell pixel; all four changed wire
headings were viewed, while other24 PNGs are byte-identical to viewed originals.

Both protected GFX families/ROIs/profiles/JPEGs retain independent-reference,
non-GT labels and training exclusions. Sky stays smooth, building soft, foliage
painted, coarse fence geometry retained. Global support creates visible broad
diagonal cab ripples; local support suppresses much of them without recovering
the fine lattice. Six extra native stress ROIs center the largest local-minus-
parent camera-RGB correction, selected after inference, with no exact reference
claimed at those extra coordinates. Residual periodic changes remain, especially
cab. Largest building correction is near a clipped highlight; it is not a direct
quality-error measurement. All six stress boards and the corrected curve were
viewed. Source/ROI/noise/exposure/configuration/parent metadata are retained;
no crop pixels are resized and no per-method display tuning is used.

Numerical/adoption/lineage checks now pass35 tests (0.66s): all-CFA NaN holdout
invariance, direction/color conditional independence, parent replacement,
native truncated boxes, zero-noise identity, exact input/output adoption and
actual-parent rejection. Frozen pilot/panel runs separately passed28/33 checks.
All numerical stage bytes are frozen; future label metadata corrections do not
change predictions. Full-frame102MP integration/speed are unverified, and the
experimental API currently requires axes divisible by four/minimum256.

Started the full fixed three-prior panel:1152 images,384 role triplets,
global/local primary threshold2 only, with12 verified pilot bindings for
adoption and1140 new analytic cases. Source/config/thresholds are fixed before
full results. Owner280342/create1794850180.3, child280343/create1794850180.34;
CPU-only,2-core affinity/low priority,32GiB RAM/96GiB disk floors,4h prediction
limit, no retries. All outputs close before complete target scoring. V143
procedural lineage is explicit in the addendum/corrective watcher; the original
V132 full-model run remains active separately. Full-panel statistics and native
review remain pending. V120 remains the general recommendation.

Publication checks verify36 unchanged receipt/source archives,34 native PNG
copies and459 local Markdown links. Current-stage Ruff check/format passes for
all six Python files. Exact live observations capture panel259/1152 and V132
step5800, with the label-correction watcher also live. These are progress
observations, not terminal claims. Both long runs retain their original owners.

[Pilot report](../docs/local-validated-waves.md) ·
[Exact receipts/source](../docs/results/local-validated-wave-pilot-v1/publication.json).

