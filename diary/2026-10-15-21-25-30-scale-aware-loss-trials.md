# Scale-aware supervision trials

Previous turn was progress: completed the matched V24/V25 review and learned
that raw innovation did not improve real scores or coarse residual error.
The full quality/speed goal remains open. No previous training jobs remained.

Implemented opt-in multiscale measured-CFA loss for synthetic and paired
training. It scores 4/16/32 packed phase block means (8/32/64 sensor pixels) in
summed input-noise units derived from clean-reference signal and shot/read
coefficients. Only complete valid blocks count; ADC-only and clipped synthetic
regions are excluded. Real targets use measured reference CFA samples, not AHD
fine interpolation. Input independence is a proxy, not posterior covariance.
Default weight zero preserves old losses. Finite/nonnegative validation and
exact-resume loss-weight checking added. No inference changes.

All 196 tests passed in 10.58 s; Ruff passed. Coverage includes analytic units,
all CFAs, CPU/CUDA FP32 physical arithmetic, fine-error nullspace, invalid/
clipped/ADC masks and zero gradients, AHD independence, both training objectives,
exact resume and frozen weights. Genuine DINO/V16 warm start is bit-identical
for 6,291,456 RGB values over four CFAs and ADC/noisy observations.

Started V26 (weight0.01) and V27 (control0) from the same V16 EMA, identical
27,696-parameter factor8 coarse branches, seed46 and LR5e-4. Planned5000
schedule, predeclared stop1000. Original body/DINO/fine branch frozen; original
50/50 paired/Commons data and losses retained. Per-step RNG and sampled hashes
support matched data. Protected final/GFX scenes and native substitutions excluded.

Live job sessions45171/47792, logs `.cache/train-scale-{loss-v26,control-v27}-1k.log`.
At step200 sampled hashes match, losses/gradients finite, about0.255s/step per
arm, CUDA peak1.386GB each, system memory available70GiB. New term changes
coarse gradients substantially; no quality gain claimed. Do not restart on
observation timeout. Source/manifests archived per run.

Method and startup receipt: `docs/scale-aware-supervision.md` and
`docs/results/scale-loss-v26-v27-startup.json`. Next: complete the first review
with both real panels, synthetic screen, flat scales and native paired/GFX crops.
