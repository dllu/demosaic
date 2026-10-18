# Complete V72 development-camera CPU review

The previous goal turn made progress: V72 completed the first32,000-example
gate and42 selected CPU photo/GFX triplets were inspected. This turn used the
available CPU for the complete existing known/unseen development camera panels
while DINO training retained the GPU.

Actual CPU worker2412063/1792296249.21 completes and exits:4known/5unseen
scenes,8/10captures,72/90crops,7methods,504/630records. V72 and originalV71
both represent32,000 example draws; units, training precision and optimizer
grouping differ together. CPUFP32/NCHW/batch1, nice10, fixed existing prepared
inputs, no CUDA/original-drive access. Exact prefix/final state/source/schedule
and all82 source/noise checks precede inference. Frozen producer and all inputs
remain under `/mnt/external/demosaic/benchmarks/packed-isotropic-mixed16-no-dino-camera-CPU-v1/`.

Known/unseen measured-CFA means: V72 47.01273584/43.57982945 versus V71
44.18252569/41.43804673. Gains2.83021016/2.14178272dB; all nine scene gains
are positive, range1.9342–3.2947. Paired1000-scene-bootstrap intervals are
[2.48171,3.17871]/[2.03356,2.23557], not training-repeat intervals. V72 remains
7.0720/10.1884dB below RawNIND channel-CFA and below Wiener7+Malvar. No promotion.

Independent case coverage/summary arithmetic verifies all1134records,18metric
comparisons and6classical witnesses, maximum7.11e-15 arithmetic discrepancy.
All16 native triplets are represented and viewed on the actual native board.
Readback of32 outer noisy/AHD panels from hashed prepared NPZs is bitwise exact
at8-bit display; all24 board cells also match. No crop resizing. This is not a
denoisedF32 replay or an independent rendering-definition audit. AHD is auxiliary,
not exact RGB GT. Two exact-synthetic-GT V72 triplets accompany the public report.

Public report: `docs/packed-isotropic-mixed16-V72-camera-CPU.md`.
Receipt: `docs/results/packed-isotropic-mixed16-V72-camera-CPU-v1.json`.
Five additional native image assets are copied byte-for-byte; earlier fixed
synthetic/GFX assets remain unchanged. Existing README/V43 reference stays fixed.

Also inspected primary JD3Net v2 training text and pinned author configurations.
Current upstream commit remains47489cbe3eba746e13ad8be8898956d7895f1835.
The larger synthetic-Bayer recipe uses1M updates/B20/128px, AdamW1e-3,
betas.9/.9/decay0 and PSNRloss; the small checked-in config differs from the
paper's small-model patch/batch text. This is task/budget context, not a compute-
equivalent schedule recommendation, reproduction or architecture comparison.
Sources/constants are recorded in `docs/results/jd3net-training-budget-context-v1.json`.
No upstream model implementation or weights are incorporated. Current recipes
and original horizon stay unchanged.

DINO child2404322/1792295586.28 remains live under controller2339549;
review2362748/1792295060.93 remains correctly waiting. Last verified DINO
optimizer1125/18,000 examples. Main training/review sources, manifests and guards
remain unchanged; protected-final scoring remains closed. Full matched quality,
SOTA, large real-photo superiority and100MP/10s remain unproven/unmet. Goal stays
active; this turn is progress, not completion.
