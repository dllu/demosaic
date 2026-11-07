The released NLFeMF checkpoint does not improve our fine-wire goal in this
pipeline. Direct Malvar and the DINO-parent hybrid recover respectively
2.533% and 2.406% of constructed mesh amplitude, versus V169 EMA's3.837%.
Present-mesh RMS rises6.96–7.56%; absent-field RMS rises8.02–8.85%. The nominal
cab prior erases much of the green fence, and the alternative prior gives
speckled, incomplete strands. Neither reconstructs the crossing family.
The main coarse fence is also rougher and less continuous. Sky appears smooth
at ordinary display, while building and foliage show no decisive new gain.

There are useful but limited quiet-field results. Compared with V169 EMA,
quiet spatial RMS falls6.26–7.74% at ISO6400 and29.27–32.71% at ISO12800.
Total quiet RMS instead rises2.15–4.09% and9.28–11.66%; DC color error rises
24.30–27.58% and101.07–103.01%. Native crops show purple/red casts and residual
blobs. Native512 coarse-flat means fall15.79–15.87% and19.22–19.38%, improving
16/24 and22/24 inputs for either return. ISO12800 total-flat RMS falls1.71–3.30%,
while ISO6400 total-flat RMS rises17.67–19.03%. A smoother field alone is not
sufficient for fidelity.

Faint/dark natural textures weaken: retained-photo band response falls28–37%,
with higher RMS in all128 method/input comparisons in that cohort. Low-noise
ADC-only photo and plane controls show a fine periodic colored pattern in both
returns, absent from the constructed GT. All72 ADC control inputs worsen in
full RMS for both returns. Direct Malvar also adds visible edge fringes;
keeping the DINO interpolation residual reduces some fringes, with higher total
quiet/mesh error. These are results for this external checkpoint, our supplied
noise maps and two RGB reconstructions; they do not establish an architectural
limit for learned matching or an equivalence to training on our free images.

All60 fixed native figures were actually viewed in15 original-detail sheets.
Keep the pinned port, sampler checks and measured coarse/spatial tradeoff as
research evidence. Retain V120 Small as the general recommendation and the
V169/V161/V165 and earlier strengths alongside their documented costs. Fine
crossings without fabricated flat-field structure remain unresolved. A future
matching experiment would need matched free-image training and explicit
low-noise/constant controls before treating these weights as a starting point.
