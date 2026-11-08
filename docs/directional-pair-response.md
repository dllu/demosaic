# Balanced directional pair-response pressure (V195)

The completed [matched comparison](directional-response-comparison.md) favors more
whole-pattern pressure for response: Whole EMA reaches 5.575% of exact GT amplitude,
4.02% above V187 EMA, with quiet spatial RMS 0.334–0.376% higher. Directional
pressure is 0.80% raw / 1.11% EMA lower in response than matched whole control,
with 0.038–0.078% lower quiet spatial RMS. Fine cab crossings and broad flat-field
mottle remain unresolved. Whole EMA is a useful stronger-response option; V187
remains the quieter immediate alternative and V120 Small the general recommendation.

For each training pair, remove each channel's spatial mean from the actual target
difference. Split its native Fourier coefficients into four angular regions, then
repeat with boundaries offset 22.5 degrees. The two tilings reuse the same target;
they are not independent evidence. Each non-DC bin belongs to one region per
tiling, with conjugate pairs kept together. Cartesian comparisons make
axis/diagonal boundaries exact; Nyquist orientations follow a declared discrete
conjugate-pair convention.

```text
r_s = mean(pair_error × t_s) / (mean(t_s²) + (1 / 65535)²)
loss = mean_over_pairs_and_regions(sqrt(1 + r_s²) − 1)
```

FP64 orthonormal Fourier reductions equal the spatial projections. The positive
1 DN16 floor limits sensitivity as a component vanishes. Averaging regional losses
reduces dominance by a large-energy direction; it cannot add a new measured
frequency. Targets and pair labels enter only after inference.

| Arm | Existing whole-response weight | Added pressure |
| --- | ---: | --- |
| Whole control | 0.25 | 0.25 × existing whole response; total 0.50 |
| Directional | 0.25 | 0.25 × eight-region mean response |

Both wrappers retain all nine original scalar terms, masks and FP32 accumulation
exactly. Equal nominal added weights do not imply equal gradient norms. Both arms
start from the same completed V187 EMA full state, including its trained
508-parameter head, with fresh identical head Adam/EMA clocks 0 and matching seeds.
Each completes 1,000 cached rows, 900 noisy updates, 3,600 images and 100 ADC skips,
with the same domain weights, schedule and clipping. All 189 inherited V183 EMA
tensors and all 103 neural sources remain fixed. This is a fresh matched stage,
not uninterrupted old Adam/EMA history.

**The response term does not penalize every false pattern.** Exactly unchanged
target pairs give zero response gradient even for textured erroneous outputs;
orthogonal errors can also be invisible. Existing absolute, pair-difference/common,
local/DC, flat-anchor and flat-spatial penalties remain essential. Actual quiet,
absent and standalone-flat checks plus held-out real captures determine the costs.

The reused CPU evidence covers 26 contracts and 53,477,376 gradient coordinates on
20 audited saved batches, with maximum FP32 gradient difference 9.10e−13 against
independent NumPy real spatial projectors. GPU admission adds seven strict donor
parities, six nonzero-head CPU/GPU checks and two genuine restored probe updates
per mode. All 2,032 head-gradient coordinates pass; both directional output
derivatives match the independent CPU reference exactly in FP32. CPU inspection
checks four probe checkpoints/eight raw-EMA states and 1,512 inherited comparisons.
Probe checkpoints never initialize training.

The full independent training audit verifies 2,000 rows, ten checkpoints,
20 raw/EMA states and 3,780 inherited comparisons. Quality covers four endpoints
× 822 cases with exact frozen V183/V169 replays, 288 ADC outputs, 144 native RGB
and 144 wave encodings, 107,544,576 native addition channels and 556 Decimal means.
All 72 figures/24 triplets were viewed at original detail; 480 actual browser crops
match 36,864,000 source RGB channels. [Completed report and hashes](directional-response-comparison.md) ·
[Final evidence](results/v195-response-final-v1.json).

Both GFX families, their JPEGs and siblings stay outside training. ISO100/AHD/JPEG
references remain qualitative, not exact GT. Sources, masks and noise draws are
cached and reused; no original/dataz access or RAW decoding occurs. The total new
local budget is 2 GiB, with no external writes; current comparisons omit recopying
all older gallery columns. [CPU preparation](results/v195-directional-response-CPU-preparation-v1.json) ·
[GPU admission](results/v195-directional-response-GPU-preparation-v1.json) ·
[Training audit](results/v195-response-training-completed-v1.json). Historical
preparation/execution corrections remain in the timestamped diary and preserved
machine receipts.
