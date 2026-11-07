# V172 local noise units for learned matching

Training is in progress; no quality gain is claimed. V171's new residual improved
standalone flats but increased quiet-color error beside detail. A diagnosis on
saved arrays found that local noise attenuation helped more than removing a
single RGB mean, while still losing to V169. This experiment retrains the same
matching network with local feature coordinates and output noise units.

The 39 input coordinates retain the same information types. RGB is centered on
its own 2×2 Bayer-cell RGB mean, which is also supplied; the cell's mean physical
variance defines its noise RMS and the 16-DN16 input-unit floor. RAW innovations,
variance ratios and noise-level coordinates use those local units. Each cell's
noise RMS scales its native RGB output. No image-wide mean/noise statistic enters
this new transform. The frozen V169/DINO result and matching network still use
spatial context, so this is not whole-pipeline context invariance or flat safety.

The network, seeded initial tensors, 1,000 cached V168 rows, pair units, frozen
V169 EMA component, V171 loss, AdamW, learning rate, clipping and EMA are unchanged.
The training/runtime function ASTs, criterion bytes and recipe fields are checked
against V171. Local input coordinates and output amplitude change together;
their individual effects are not isolated. The old image-wide units remain in
the unchanged training criterion. No released V170 weights are loaded.

Zero supplied local variance retains the frozen result at that cell, including
signed zero; wholly ADC-only rows bypass matching and skip updates. The image
noise unit is an amplitude convention, not calibrated RGB covariance. Targets,
clean flat masks and counterfactual pair labels are used only by the unchanged
training objective and never enter inference.

All 126 relevant CPU checks pass, including 12 new tests of independent NumPy
cell statistics, four Bayer layouts, phase output units, zero-variance routing,
uniform-field equivalence and feature locality under distant bright changes.
The actual initial state equals the seeded V171 state. New synthetic admission
uses three batch4 native512 backwards and one native768 inference, with6.26GiB
peak CUDA. The unchanged sampler/core inherits V171's pinned-source adjoint and
CPU/CUDA parity evidence; those old primitive calls are not repeated or counted
as new work. The sampler's atomic CUDA input-gradient remains nondeterministic.

The same fixed 1,000-row schedule restores a real step8 checkpoint and continues
at9 without replay. Raw and EMA endpoints are declared before held-out inference.
Both evaluate all822 cached cases and must exactly replay their1,644 frozen
V169 outputs, including144 exact ADC final identities. V171 EMA and V169 EMA are
both comparison baselines, so repairing V171 alone will not establish a gain.

All method rows stream metrics and fingerprints. Full arrays are retained only
for36 preselected native cases:72 RGB+72 corrections,430,196,736 bytes. Independent
posthoc checks will cover those selected arrays; there is no complete new-array
archive. The fixed48 boards/12 noisy-restored-exact constructed GT triplets keep
160px crop pixels, coordinates, camera transforms, noise, exposure and contrast
unchanged. Both protected GFX scenes, cab priors/windows and JPEGs remain included.
ISO100/AHD/JPEG references are qualitative, not exact GT and not pixelwise scored.
Original media and `/mnt/dataz` are unused; the scene families remain out of training.

The trial declares52/114GiB local/external reserves plus.5GiB projection margin,
32GiB runtime RAM and24GiB CUDA, with52GiB launch RAM. No new source/noise draws or
parent/DINO calls are needed. All95 prior neural files remain unchanged. Existing
recommendations and measured strengths stay visible while quality is pending.

[Prepared sources](results/v172-local-noise-matching-preparation-v1.json) ·
[CPU and metric-runtime readiness](results/v172-CPU-runtime-readiness-v1.json).
