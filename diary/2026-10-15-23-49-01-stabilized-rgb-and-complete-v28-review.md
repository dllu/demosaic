# Complete V28 review and matched stabilized RGB trial

V28 completed its original 5,000 steps. Full 427-photo synthetic PSNR/SSIM is
32.97457/.940248 versus V16 31.48800/.923018: +1.48657 dB, source-bootstrap95%
[+1.35947,+1.58359]. Known/unseen real measured-CFA means54.11062/53.65897
slightly exceed RawNIND54.06860/53.56220, but intervals include zero and RGB
PSNR/SSIM still trail it. Native GFX foliage/fence retain colored texture and
soft irregular detail. Published complete numerical receipts and at least two
native exact-synthetic-GT triplets in docs/pretrained-rgb-v28-5k-review.md.

Implemented an optional centered GAT/expectation-inverse representation for the
pretrained RGB/DINO architecture. Explicit physical shot/read conditioning is
routed through training, development evaluation, GFX and full tiled inference.
Transforms use float64 intermediates with FP32 boundaries; pure Gaussian and
zero-noise cases have separate linear fallbacks. Stabilized Malvar interpolation
has no WB scaling; DINO previews retain ordinary camera/WB rendering. Fixed
high-read inverse-table cancellation with centered Hermite quadrature. Existing
V28 checkpoints keep their original behavior through default-false flags.

V29 reused all exact V28 step-zero neural tensors and matched seed/data/LR/mix.
All41 logged batch hashes/domains through1k are equal; unlogged batches were
not independently hashed. Completed first1k: 16-photo screen34.76093/.957497,
+1.32563dB over matched V28. Known real54.14376/39.73981/.929373 improves;
unseen53.59622/37.91679/.913810 is mixed and below RawNIND rendered quality.
Native GFX structure improves but remains soft with irregular wires/hot dots.
Published docs/stabilized-rgb-v29-review.md, complete receipts and native crops;
updated README with current synthetic and foliage/fence representatives.

A synthetic clipped-white observability probe exposed ISO calibration lost by
range normalization. Added optional physical measurement black/white anchors
and noise-family/read-ratio conditioning in three otherwise constant channels,
without additional neural parameters. Measurement anchors obey the algebraic
transform relationship; denoised estimates use the expectation inverse. Added
invariant/round-trip/gradient/clipping tests. Full suite238passed19.18s; Ruff
passed. Rebuilt the wheel with isolated build dependencies and verified exact
code plus upstream license notices. An initial no-build-isolation attempt
failed because hatchling is intentionally outside the runtime environment;
normal isolated build succeeded without changing runtime dependencies.

Prepared V30 with identical V29/V28 neural initialization, frozen manifests,
data schedule and1k review gate. Genuine DINO BF16 CUDA backward with anchors
passed: FP32 finite output, nonzero gate/input-adapter gradients, no frozen
backbone gradients. Its startup receipt is
 docs/results/stabilized-rgb-v30-startup.json. No quality result is claimed yet.
More Commons originals download independently; no active manifest changes.

Final quality, protected-final evaluation, matched modern-trunk DINO ablation
and sub10s/100MP target remain unmet. V29 is not extended before reviewing the
anchored trial, and no GFX data are fitted or trained on.
