# Review the competing-orientation head on identical observations

Recorded: 2026-11-16T03:58:23-08:00 (America/Los_Angeles).

The competing-orientation trial has completed both raw/EMA endpoints on all
822 cached inputs. All 60 native boards and 12 triplets were inspected in 15
original-pixel sheets. The new shared staging tool verifies 8,294,400 candidate
RGB channels against saved native predictions and 20,889,600 retained channels
against original panels. Its preflight reproduces the completed shared-edge
study exactly, including all four independent directional checks. Receipt copies
preserve decompressed bytes. No new source, noise or parent/DINO inference is
needed by training, the full review, native staging or directional scoring.

There is a specific directional gain: mesh2302's weaker Fourier-sector response
rises 28.412%→33.551% at EMA (raw 28.077%→33.167%). The dominant sector falls
57.873%→51.106%. This gives a somewhat clearer second orientation in the native
view but still rounded/merged wires and incomplete crossings. Mesh2309 is a
counterexample: weak sector 17.272%→15.881%, dominant sector essentially unchanged
at 92.005%. These are full-template orientation sectors, with mask/harmonic/
intersection leakage, not exact isolated wire-family amplitudes.

Overall mesh projection falls 11.10184%→10.60738% at EMA. Present-mesh full RMS
rises 8.24012→8.25960 DN16; p95/max paired increases are +0.20890/+1.58101 DN16.
Quiet means improve 0.012–0.043%; cached fresh-flat means improve 0.062–0.070%.
Some cases worsen, including maximum quiet increases +0.02984/+0.09194 DN16 at
the two priors. All 32 ADC metric groups match exactly at both endpoints.

Both protected GFX scenes, foliage/chain-link/sky/building detail, both cab ROIs,
both cab noise profiles and both JPEGs were reviewed. Building green/magenta
fringes persist. Cab modulation remains visible without a decisive improvement
in complete crossings. Amplified absent/gray/blue/quiet controls retain false
periodic texture; natural photos retain soft detail and faint background ribbing.
Independent ISO100/AHD/JPEG references are qualitative, not exact GT or scored.
V120 remains the general recommendation; the local directional gain and its
counterexamples remain documented rather than suppressed by aggregate ranking.
[Complete report and native provenance](../docs/competing-orientation-comparison.md).

Raw export SHA256:
`098cb3b5e3d090bd924dc40a832443d570fbad1b1825ecd25fcba31e787f1d4a`.
EMA export SHA256:
`d4261136f71e888637cbfdc43dbe973f8c12488d6544e3482c852332c1ca102e`.
The second worker is continuing the three-profile conditional-increment review
on the same 1,152 fresh-noise observations. Contexts are recomputed for the new
selector; actual anchor/full-forward checks precede readout/gain reuse. Its
result is pending at this observation, so the one mesh's sector gain is not
substituted for a conditional-increment/quiet-error improvement.

Validation now covers 48 focused tests, Ruff, exact default source-bootstrap
replay, full prior native staging and four exact prior directional projections.
The paired candidate reporter rejects observation/condition/coverage changes,
nonfinite metrics and changed zero-gain anchors. Reporting sources and actual
validation evidence were frozen before analyzing the completed new endpoints.

Follow-up completed: 2026-11-16T04:20:25-08:00 (America/Los_Angeles).

The three-profile cached review is now complete: 384 physical triplets/1,152
observations, two endpoints and five gains, reusing the exact previous inputs.
All 905,969,664 anchor RGB channels match saved V195 exactly; 14,155,776 actual
full-forward channels verify readout delivery. Readouts/anchor/CPU-CUDA RNG stay
unchanged. All paired identities/conditions and zero-gain metrics match.

Far-edge EMA weak increment response rises 1.496%→1.693% at the6400 prior,
3.133%→5.063% at1600, and 8.140%→14.199% at400. At1600, the weak gain is
+1.930 percentage points [0.185,4.477], quiet RMS improves 6.90562→6.89694 DN16,
and weak increment error improves 15.11652→15.03832 DN16. Strong response falls
60.637%→46.336%. At400, weak gain is +6.059 points [1.600,11.016], weak increment
error improves 10.51200→10.45593 DN16, but quiet RMS rises 5.99346→6.00302 DN16
and strong response falls 86.741%→70.832%. Those quiet differences are not
presented as equal-error endpoint gains. Near6400 weak response still declines.
All six full-image RMS means worsen. The same eight sources underlie all
profiles; related CFA/repeat views are averaged within source, and 5,000 paired
source-bootstrap draws provide exploratory intervals, not formal risk control.

All12 new native comparison boards and all3 gain plots were actually viewed.
The two retained source views still largely show one direction and incomplete
crossings; the aggregate weak gain does not make their output close to exact GT.
Public crop cells preserve source/reference pixels, shared transforms and the
same160-pixel coordinates. Exact original receipt bytes remain archived.
[Completed conditional-response report](../docs/competing-edge-response.md).

The new `competing` preset exposes the implementation without making it the
general recommendation. Both actual raw/EMA exports load through the public
registry with all197 legacy tensors exact and family_degrees20 retained. The
lightweight registry boundary test passes after that catalogue addition. All32
ADC metric groups remain exactly equal, and the eight available original native
ADC cases replay 4,521,984 RGB channels exactly at each endpoint. The other64
ADC cases have original metrics, not retained baseline native arrays, and are
not claimed as pixel replays.

This supplies a measured weak-increment improvement on the constructed panel,
with strong-direction losses, mixed quiet effects and persistent real artifacts.
The next architecture needs to retain useful strong-family carriers while
adding weak-family evidence; a fixed equal quota does not do that across scenes.
No worker remains running for this completed trial, and no broader quality or
speed target is declared achieved.
