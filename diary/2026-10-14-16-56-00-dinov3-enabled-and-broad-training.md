# DINOv3 enabled and broad training

The initial 8192-source preparation completed: 7378 train, 427 validation,
387 untouched test, three corrupt/unreadable images skipped and 147 unaccepted
license records omitted. Saved an immutable `commons-8192.jsonl`. Full-corpus
preparation is now running separately with four bounded workers, reusing caches.

The official HF repository returned 200 on recheck. Downloaded real DINOv3
ViT-S/16 weights, revision `114c1379950215c8b35dfcd4e90a5c251dde0d32`.
A real CUDA BF16 forward/backward verified 21,596,544 frozen backbone parameters,
finite output/loss, nonzero gate gradient (0.00746 aggregate in the diagnostic),
and no frozen-backbone gradients. No fallback model was used. Backbone revision
is saved in model configuration and frozen weights remain excluded from EMA and
restoration checkpoints.

Started `configs/dino-8192.yaml`, initialized from highlight-v2's step-5000 EMA,
with a new optimizer, corrected reference highlights, camera metadata, rendered
highlight masking, and physical ADC black offsets. Target: 20000 steps, batch 4.
The run passed step 800 with finite losses, about 0.073 s/step and 0.943 GB peak
CUDA allocation. This is training evidence, not proof that DINO improves quality.
The run snapshots actual code, lockfile and manifest; resume preserves per-version
source snapshots. Source manifest rows are captured once for train/validation so
an atomic replacement during preparation cannot silently change either dataset.

The completed no-DINO highlight-v2 run at step 5000 scores 37.216 dB linear /
32.857 dB rendered on the fixed 61-source validation, versus RawNIND CFA-LS
33.756/28.914 and bilinear 36.017/31.765. Its controlled highlight chroma error
was reduced about 66% relative to bootstrap at step 3000. Full real-world quality
and state of the art remain unproven.

Verified native RAW reading for GFX100S, GFX50R (51 MP, including different green
black levels), Leica Q2 (47 MP, GBRG) and Sony a7R II (42 MP). Originals were not
modified. Private architecture/ocean/sky crop comparisons are local in
`evaluation/real-crops-v2`. RawNIND smooths sky/spray more aggressively; our model
retains more grain/texture. This is not an unqualified perceptual win. The sky
crop has no aircraft edge, so additional edge/detail and high-ISO cases are needed.
No personal images have entered training.

Optimized CPU input-finiteness validation with a zero-copy NumPy view instead
of multiple full-image Torch intermediates. The trained highlight-v2 completed
an actual warmed 100 MP reconstruction in 9.341 seconds, with 0.747 GB peak CUDA
allocation. A concurrent-evaluation timing was explicitly marked as contended
and excluded. Decode/encode and final DINO-model timing remain separate gates.

All 27 tests pass; Ruff and diff checks pass. Environment configuration now also
keeps Matplotlib/XDG config and CUDA compiler caches in authorized storage.
Next: verify the first DINO checkpoint reload, finish/evaluate broad training,
compare a matched no-DINO run, measure real noise conditioning and inspect more
texture/highlight/high-ISO examples before claiming completion.
