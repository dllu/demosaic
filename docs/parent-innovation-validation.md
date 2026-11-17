# Fine innovation validation on an A-only neural prediction

**Implementation/tests and both48-case numerical reviews are complete. Native
actual viewing and the quality decision remain pending.** This adaptive control
was admitted before the user's whole-scene-context steering; it remains distinct
from the [next scene-context architecture test](whole-scene-context-next-test.md).
No whole-photograph semantics are added by this change.

The completed [full guided](neural-guided-phase-full-panel.md) and
[coloured fine-wire](coloured-fine-wire-benchmark.md) reviews show why standalone
nuisance-prediction improvement is insufficient: the delivered neural-parent
correction can have higher weak-increment error. The opt-in
`fine_validation="neural-parent"` tests a closer A-only composition.

For each discovery fold, form the predictor from its genuine A-only neural RGB
field plus both unshrunk full-fit sinusoidal fine innovations computed from
RAW minus that field. Each null removes one delivered direction while retaining
the other. Pool held-out full/null gains over actual CFA colours with the existing
joint score. Require both matched folds and the original fixed threshold(s).
The default remains`"nuisance"`; enabling the new target requires joint support
and sinusoidal additional fine carriers.

Fine discovery, global nuisance, local full-fit RGB coefficients, actual final
RAW-minus-full-parent delivery, broad guided phase and raw-H1 controls retain
their existing definitions. Full-input parent never enters validation. This
scores an **A-only teacher plus unshrunk fine composition**, not the final
shrunk broad+fine/full-input estimator; it is not calibrated final-image risk.
In particular, it does not resolve semantic ambiguity by itself.

114 relevant regression tests pass. New checks cover exact delivered full/null
maps, signed independent RGB amplitudes across allCFAs, zero innovation when
the A-only teacher already equals the observation, invariance to withheld NaNs,
mask mismatch refusal, unchanged broad/H1 controls and full-input-parent
invariance of validation records. No learned weights change.

Two frozen producers completed all96 cases before any new GT/reference review:

|Cohort|Parents/teacher|Cached A-only fields|Thresholds|Correction time, two CPU threads|
|---|---|---:|---|---:|
|Original48-case materials/GFX/development pilot|Procedural V143; real and teacher V120|88|0/2/4|603.59s|
|Fresh coloured48-case follow-up|V120 for parent and teacher|96|2|593.22s|

These are CPU correction-stage timings, not100MP/end-to-end inference. The
original pilot's teacher/parent mismatch is disclosed; the coloured cohort is
the cleaner same-V120 composition test. Both background stages rechecked actual
physical/mask/argument fingerprints and used **zero fresh root/DINO forwards**.
The coloured pair retains96 exact H1 comparisons across48 physical cases.
All original four coloured variants,400 score rows and40 actually viewed figures
remain unchanged. New208 rows/4368 direct norm/dot/cross-product checks and40
new fixed-ROI native figures are prepared. The pilot's standard finite/material/
native independent audit also passes. No threshold, crop or new noise seed was
selected from results; actual viewing is the next separate review step.

Both standing GFX families remain in the original pilot: DSCF3879/3880 sky,
building, foliage and coarse fence; DSCF3842/3835 both fine cab ROIs/profiles/
JPEGs. Independent ISO100/AHD/JPEG references are qualitative, not exact GT,
and receive no pixelwise scoring. Cached media only, originals read-only;
protected captures/JPEGs/siblings stay outside training.

Pilot plan`18be92d7a04751d37a3f49b5aa9a0b75344dc03431302ebfb7f3858df5ed88eb`;
coloured plan`0b61c598959bfbcfe29e118136b5aece5ccac2e5a3e0e7daeac9353fb6da56b8`.
[Exact source/terminal/audit/test receipts](results/parent-innovation-completed-pre-review-v1/publication.json).
