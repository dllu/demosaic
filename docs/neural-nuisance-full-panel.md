# Full neural-nuisance source/CFA/noise review

The [fixed-proposal neural-nuisance variant](neural-nuisance-fixed-proposals.md)
is now being evaluated beyond its two-source pilot. **Results are pending.**
The current measured operating point remains the completed pilot; this larger
run does not yet establish broader quality or change the general V120 choice.

The frozen cohort contains1152 procedural roles:
8 source geometries ×2 edge placements ×4 Bayer layouts ×2 independent-noise
repeats ×3 present/absent roles ×3 original noise priors. All12 material and
standing real-photo contexts are retained, giving1164 cases. The full panel is
an existing development cohort, with synthetic geometries already examined in
the earlier analytic H1 study; it is not an untouched photographic test set.

The intervention is unchanged from the preferred pilot: whole-context A/B
neural backgrounds, one shared global sensor partition for all overlapping
tiles, analytic edge/variance proxies, fixed analytic H1 frequencies, own-color
neural nuisance, conditional held-out validation and full-minus-null delivery.
Six controls retain global/local support for raw-wave analytic H1, conditional
analytic H1 and conditional neural nuisance. The fixed threshold is2; the
pilot retains the0/2/4 curves. No fresh sensor corruption/source observation,
RAW decode, learned-weight update or training admission is involved.

The complete pilot's48 cases supply288 exact threshold2 outputs and88 exact
background fields. Their actual RAW/CFA/parent fingerprints, finite native
predictions and the entire package source snapshot match before adoption.
The remaining1116 cases require at most2232 fresh root/encoder forwards.
All2320 background fields and all1164 corrections must close before new full
GT/reference scoring. Four explicit zero-noise cases bypass the neural stage.
Stage reserves are48GiB RAM before neural loading,32GiB during execution and
96GiB free disk, with a six-hour stage deadline. The original training worker
is neither restarted nor signaled by this review.

Procedural parent: V143
`96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4`.
Photographic parent/background teacher: V120
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
Official DINO backbone:
`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.
All three procedural parent bindings match the corrected full-panel lineage.
Fresh inference checks all91 restoration tensors and the backbone unchanged;
cache adoption checks actual input/mask/argument/field hashes.

The separately frozen [reviewer](../scripts/review_neural_nuisance_panel.py)
streams independent scalar checks over all2688 method/group rows and8064
absolute role rows. It reports all64 CFA/repeat views per source/noise/placement
cell, eight paired source-cluster differences and exact empirical bootstrap
percentiles over8^8 ordered source resamples. These are descriptive conditional
statistics for eight development geometries, not calibrated camera-population
confidence. Its parameterized summary reproduces all previous full-H1 means,
contrasts and bootstrap fields exactly; the initial rehearsal's whole-wrapper
assertion failed only because the archived wrapper also stores its input rows.
Both attempts are preserved.

Native selection is fixed before results: all48 RGGB/repeat0 two-direction
source/prior/placement views, ROI`[176,176,160,160]`, exposure2/contrast1, plus
every material/protected context. The reviewer produces matched native160
comparisons, noisy/restored/exact-GT triplets and additional maximum-correction
real stress views. Actual viewing and publication follow the numerical audits.
DSCF3879/3880 sky/building/foliage/chain-link crops and DSCF3842/3835 left/right
cab mesh, both noise profiles and both JPEGs remain in the review. Independent
ISO100/AHD references differ in aperture/exposure/motion and are qualitative,
never exact GT or real-photo pixelwise scoring targets. All protected media and
siblings remain excluded from training; original files remain read-only and
the local caches are used.

Producer plan SHA256:
`acf7f881a2f23fae4250525a7bafc93d368304732e14fa348ff590bf136ff5ad`.
Review plan:
`e092e0eeed3997a4eac797e00d5e54bc08c4954a00104aac27c824e4c1b761e8`.
Execution roots are `.cache/experiments/neural-nuisance-full-panel-v1/` and
`.cache/experiments/neural-nuisance-full-review-v1/`. Existing pilot receipts,
predictions and published images remain unchanged.
