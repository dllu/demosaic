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
