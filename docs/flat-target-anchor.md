# Clean-target flat-region anchoring: V162

V162 is training a matched loss comparison on the stronger
[V161 frequency-context architecture](harmonic-frequency-context.md).
V161 raises learned mesh response another 21–22% over V160 paired response,
but quiet RMS worsens another 5–7%. Its boosted exact-flat views show false
colored/gridded grain and increased RGB bias. This trial adds direct target
supervision where the clean target is locally flat. Quality remains pending.
[Immutable readiness and sources](results/v162-flat-target-anchor-preparation-v1.json).

Both fresh heads have 124,397 parameters across 46 tensors. They share all
1,000 cached V160 B4 batches, common initialization, V161 paired-response weight
1, RGB/gradient/delivered-spectrum/local-regret/regional-DC losses, AdamW,
clipping and EMA clocks. Only the new anchor weight differs: 0 versus 0.25.
All 88 neural source files remain unchanged.

For each target pixel, a detached training mask checks the native 17×17
neighborhood. The maximum minus minimum must be at most 1 DN16 in every RGB
channel. Borders use the truncated neighborhood. Spatially constant colored
fields qualify; differences between RGB channel means do not disqualify them.
Separable extrema avoid variance subtraction and averaging artifacts.

The anchor penalizes actual output-minus-target RGB error in fixed 16 DN16
units, using `rho(z) = z² / (sqrt(1 + z²) + 1)`. Its mean includes all image
elements, so a sparse mask receives proportionally less weight. The existing
domain weight also applies. ADC total weight remains zero. A selected weak
gradient is supervised against its real target values: the loss does not
replace the target with a constant or penalize a correction toward the target.
The fixed unit is a training scale, not calibrated RGB uncertainty.

Pair-difference supervision cancels errors shared by both members. Ordinary
RGB losses still constrain them, but their image-noise units can be much larger
than the pair units. The new term supplies additional absolute supervision
on eligible regions. This is a hypothesis about improving the observed
tradeoff; it gives no inference-time flatness guarantee. Targets, masks and
pair fields never enter the model forward.

156 CPU checks pass, including 17 new independent mask/loss/adjoint, border,
coverage, common-error, batch-independence and sub-DN-detail checks. CUDA parity
passes 28 archived contexts / 56 actual head calls across all CFAs and native
256/384/512/768 contexts. Ten additional prefix leaf-output backwards check the
actual CUDA masks, losses and gradients against independent NumPy arithmetic;
these are not neural forwards. Maximum adjoint difference is 1.12e-9.
Genuine 8+2 model/EMA/Adam/RNG restoration passes, with 92 finite Adam states
and nonzero finite prefix gradients for all 92 parameter tensors. The first
40 control trace rows exactly match V161. Smoke CUDA peak is 6.753 GiB.

The original run trains both heads for 1,000 updates. The control must match
every V161 harmonic trace row and final raw/EMA/Adam state. Main review then
evaluates all four fixed raw/EMA endpoints on 822 cached cases, with 3,288
actual calls. All 1,644 control predictions must replay exactly before their
storage is reused; all 1,644 new candidate arrays stay external. There are
no new parent/DINO forwards, source constructions, sensor draws or RAW decodes.

The fixed native review has 48 boards, 24 noisy/restored/GT triplets and six
retained comparator columns: V156 raw, V157 EMA, V158 EMA, V159 EMA, V160
ordinary EMA and V160 paired EMA. The four current endpoints include exact
V161 controls. All cells remain native 160×160, with 54,451,200 RGB channels
to check and 18 original-detail sheets to inspect after rendering.

Both protected GFX scenes remain included: DSCF3879/3880 sky, building,
foliage and coarse fence; DSCF3842/3835 fine cab mesh under both priors/windows,
plus camera JPEGs. ISO100 aperture, shutter, motion and processing differ;
these are qualitative references, not exact GT or pixelwise scoring targets.
All protected captures/JPEGs/siblings stay excluded from training.

The new study reserves 60/152 GiB local/external plus 0.5 GiB projected margin
and a 12 GiB CUDA quota. Prior arrays and machine receipts are preserved.
Original drives and `/mnt/dataz` are unused. Planned scientific work totals
5,364 head calls / 11,424 image evaluations, excluding separate CPU tests and
the ten leaf-output loss checks. Final quality and actual native viewing
remain pending.
