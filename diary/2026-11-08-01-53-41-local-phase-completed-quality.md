# Local phase evidence: stronger mesh response with a quiet-field cost

Recorded: 2026-11-08T01:53:41-08:00 (America/Los_Angeles).


The original local training, review and completion controller are terminal.
Training owner PID 786037/create 1794130035.47 completed all 1,000 cached rows,
900 new updates, 3,600 images and 100 ADC skips. The completion controller
PID 791120/create 1794130922.7 adopted that exact launch, audited training,
launched the two-endpoint review once, audited quality, reduced tables and
rendered native crops. It stopped for actual inspection. No prefix was repeated.

The full training trace, 900 FP32 totals and all five checkpoint raw/EMA/Adam/
frozen/RNG states pass. Existing 141 network Adam states finish at 1,800; the
local adapter finishes at 900. Genuine row8 restoration continued at row9.
Final training checkpoint SHA256:
`9c749aa681260bb79ec11b077c596c7dc68bb35c099ddcf44670d8bcfe8e6af8`.
Peak CUDA allocation was 6,741,187,072 bytes, about 6.28 GiB.

Both endpoints use all 822 fixed inputs: 1,644 wrapper/frozen calls, 1,500
matching/projection calls and 7,500 sampler calls. All 1,644 exact frozen
replays and 144 ADC identities pass. Independent quality verification covers
6,576 input fingerprints, 72 native RGB plus 72 residual arrays, 53,772,288
addition channels, 582 recomputed metric scalars, 278 Decimal means and 750
exact raw/EMA input-only local metadata pairs. Geometry/power metadata checks
are not independent spectral recomputation or calibrated confidence.

Raw/EMA mesh response reaches 4.521940% / 4.548425% of constructed GT amplitude,
15.229953% / 15.926311% above same-endpoint global V178. Only 122/256 raw and
142/256 EMA pairs increase. Relative to control, response rises 16.290407% /
16.986805%; relative to V172 EMA, local EMA rises 17.312568% with 184/256
increases. Less than one twentieth of true mean amplitude is retained.

Against global V178 EMA, quiet spatial RMS rises 1.054126% / 0.785815% for
ISO6400/12800, with 31/32 inputs worsening. Quiet total rises 0.843577% /
0.510595%, with 30/32 worsening. DC changes +0.272294% / −0.278988%. Raw has
similar spatial/total costs. Mesh-present blank RMS rises about 0.10%; absent
full RMS rises about 0.04%. EMA standalone full-flat changes −0.029900% /
+0.000933%, while spatial error rises 0.021062% / 0.041907%. Natural band
response gains are tiny, with mostly slightly higher relative band error.

Actually inspected all 15 original-detail sheets/60 figures, including 12
unresized noisy/restored/exact constructed-GT triplets. First mesh stays
nearly uniform at ordinary display; contrast40 shows stronger fine periodic
modulation under broad error, without a complete recovered lattice. Second
mesh retains mainly one orientation. Both fine green cab ROIs/profiles stay
soft and incomplete, without clear new crossings. Coarse fence survives;
foliage/building and natural bird/butterfly/bark detail remain soft. Main sky
looks smooth at ordinary exposure4; amplified quiet fields retain stronger
fine mottled/striped error over broad colored mottle. ADC bark/fur/planes
retain exact frozen output. ISO100/AHD/JPEGs are qualitative references, not GT.
Protected families/JPEGs/siblings stay excluded; originals/dataz remain unused.

A first unexecuted publication-source adaptation accidentally changed a version
and fixture-field token while reducing 18 sheets to 15. Three unit checks
rejected it; source/log are preserved. The explicit V180 namespace/fixture
field was corrected before any export or public output; all 16 guards pass.
Actual publication gate rejected the then-live review before Torch import.
The marked viewer fixture checks all 480 native crops; actual browser mode
rejects those fixture records. These remain separate from actual quality.

Published two strict CPU inference exports, all 15 methods/12,330 rows/
22 contrasts/882 cells and all 60 PNGs. Both V175 endpoints and four completed
V178 endpoints remain available. The viewer defaults global V178 EMA/local
V180 EMA, with separate checkpoint/state/module metadata for all six selectable
V178/V180 endpoints. Actual Firefox checks 48 boards, both endpoint pairs,
480 crops, metadata, click/F flipping, navigation and no JavaScript errors.
All 36,864,000 captured RGB channels exactly match the actual source PNGs.
[Actual browser verification](../docs/results/v180-local-native-viewer-verification-v1.json).

Use the local-evidence architecture as the next detail-development baseline,
with V172 retained as the balanced comparison and V173/V175 raw quiet, V171
flat and V161 stronger-response strengths kept visible. This measured gain
does not solve the original quiet-sky/fine-cab goal: controlling extra response
in blank regions remains necessary. V120 Small remains the broad recommendation.
README now contains two current V180 native mesh triplets and keeps the earlier
comparisons accessible. No blind-generalization or seed-uncertainty claim is made.

The [independent publication verifier](../scripts/verify_local_phase_evidence_publication.py)
checks exact receipts, both strict exports, all cells, independently recomputed
new/retained V178 crops, source pixel copies, actual browser provenance and
local links. Its [publication result](../docs/results/v180-local-phase-evidence-publication-verification-v1.json)
is retained with the [completed report](../docs/local-phase-evidence-comparison.md)
and [exact final evidence](../docs/results/v180-local-phase-evidence-final-v1.json).
