V178 adds a small measured mesh-response option to the useful matching models.
Its evidence raw/EMA endpoints reach **3.9243% / 3.9235% of exact constructed
GT amplitude**, versus the matched control's 3.8885% / 3.8880%. That is a
**0.9203% / 0.9148% relative increase**, after the same 900 additional updates.
The gain is uneven: only 121/256 raw and 125/256 EMA inputs increase; the rest
decrease. The feature operator and its additional 3,120 learned weights change
together. This comparison does not isolate which causes the mean change.

Blank-region costs remain. Relative to the same-endpoint control, mesh-present
blank RMS rises 0.0050% raw / 0.0134% EMA, and blank spatial RMS rises
0.0137% / 0.0180%. On absent meshes, full RMS changes −0.0032% / +0.0043%;
mean signed hypothetical-template response remains near zero, which does not
rule out colored mottle. Quiet spatial RMS beside detail **rises at both noise
levels**: raw +0.0413% / +0.0110% and EMA +0.0525% / +0.0165% for ISO6400/12800.
Quiet total RMS changes raw −0.0280% / +0.0027%, EMA −0.0385% / −0.0068%, mostly
through small DC changes. ISO12800 standalone512 full-flat RMS rises about
0.011% at either endpoint. Natural-photo band-response changes are tiny and
mixed; improved response alone does not establish lower band error.

Against V172 EMA, evidence raw/EMA mesh response rises **1.2145% / 1.1958%**;
209/256 and 201/256 inputs increase. EMA quiet total RMS falls 0.0894% / 0.0518%
for ISO6400/12800, while quiet spatial RMS changes +0.0518% / −0.0257% and DC
RMS falls 0.4074% / 0.2446%. Its standalone512 full-flat RMS rises
0.1162% / 0.0151%; mesh-present blank RMS rises 0.0625% and absent full RMS
rises 0.0509%. Raw quiet total RMS instead rises 0.0351% / 0.0276%. These
costs keep V172 useful as the balanced matching baseline. V161 retains much
stronger learned mesh response at a larger quiet cost; V173 retains its stronger
quiet spatial gain, V171 its standalone-flat gain, and V175 raw its slightly
lower quiet total RMS. V120 Small remains the general model recommendation.

All **72 native figures in 18 original-detail sheets** were actually inspected,
including 24 unresized noisy/restored/exact constructed-GT triplets. In the
first mesh, the weak crossed pattern remains almost absent at ordinary display;
contrast40 reveals broad colored error. The second mesh retains mostly one
orientation and still misses the weaker crossing. Both fine green cab ROIs
remain soft and incomplete under both supplied noise profiles, with no clear
new crossing recovery over the matched control. Coarser fence strands survive;
foliage and building detail remain soft. The main sky crop looks smooth at its
ordinary display exposure4. Noisy gray/color flats and quiet regions beside
edges retain broad colored mottle at contrast40. Normal-display similarity
does not establish safety on noisy blank sky. ADC bark/fur and planes preserve
the frozen output without adding new detail.

Both protected scenes are included: main DSCF3879 ISO6400 with independent
DSCF3880 ISO100 f/5.6, plus DSCF3842 fine green mesh with independent DSCF3835
ISO100 f/5.6 and both straight-out-of-camera JPEGs. **ISO100/AHD and JPEG views
are qualitative references, not exact GT**; aperture, exposure time, processing
and moving subjects differ. No real-reference pixelwise scores are reported.
All captures, JPEGs and siblings remain excluded from training. Only cached
inputs were read; originals and unavailable `/mnt/dataz` were unused.

The native mesh triplets use ROI `[176,176,160,160]` in 512px RGGB contexts,
common display exposure8/contrast1, shot .00128 and read variance 6.5536e−6.
Fine cab crops use the cached `[600,6260,768,768]` context, native ROIs
`[206,229,160,160]` and `[426,189,160,160]`, display exposure16. Other figures
retain their original source, physical noise, ROI, exposure, contrast and
anchor in the manifest. Evidence training checkpoint SHA256 is
`581db9a1b508081332e5cb997b3171518ecf521aa73f2d464e30d27cde2a02ab`;
control is `f01f325f4a516b508847c8bfea5d38b9292a02c5c6843d22fb6317f2234be79b`.
Every endpoint records raw/EMA state, module hash, class/configuration and
strict inference-export provenance separately.

Both arms complete 1,000 cached rows/900 updates/3,600 noisy images, starting
from V172's real 900-update raw/Adam/EMA state. The old network clocks finish
at 1,800; the evidence adapter finishes at 900. Both full training traces and
all ten checkpoints pass the independent CPU audit, including EMA, frozen
weights and genuine row8 restoration. Review executes all four endpoints on
the same 822 fixed cases: 3,288 wrapper/frozen calls, 3,000 matching calls,
15,000 sampler calls and 1,500 evidence projections. All 3,288 exact frozen
replays and 288 zero-variance identities pass. Peak training allocation is
about 6.28 GiB. Neither training nor review draws new sensor noise or runs
the parent/DINO model.

The independent quality audit checks 13,152 input fingerprints, 144 RGB and
144 residual native arrays, 107,544,576 addition channels, 1,164 independently
recomputed metric scalars, 556 Decimal means and all 750 input-only raw/EMA
evidence pairs. The reducer preserves 13 methods, both V175 endpoints,
10,686 rows, 34 contrasts and 714 table cells. A first manual audit invocation
stopped before Torch import because its Python symlink was resolved to the
system interpreter; its launch/log are preserved, and the unchanged frozen
auditor passes with the explicit environment interpreter. [Execution and
viewing provenance](results/v178-completion-execution-v1.json).

This is one reused development stream and one matched continuation, with no
seed uncertainty or blind generalization estimate. The measured mesh gain
is worth retaining, while fine dark crossings and blank-field mottle remain
open. The separate V180 local-evidence variant is CPU prepared and untrained;
it supplies spatially varying measured coefficients at the same parameter
budget, with support spreading, seams, CUDA cost and actual quality still to test.
