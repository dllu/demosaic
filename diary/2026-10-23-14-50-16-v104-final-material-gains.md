# Review V104 final twenty-thousand-update material gains

Recorded: 2026-10-23T14:50:16-07:00 (America/Los_Angeles).

The previous goal work added the configurable reconstruction epsilon with
139 tests, exact default V102 training replay, 324 complete gradient-tensor
replays, corrected 4+4 resume and actual CUDA checks. Commit `486202e` is
pushed. That option does not change V104 or the frozen capacity recipes.

Original V104 completes all20,000 updates from V102 final20k EMA on the
90,872-source cohort. Original controller/trainer PID identities exit cleanly
with the complete phase registry. The queued full quality evaluation and
separate CPU material report begin without restart or checkpoint selection.
The final training result preserves the exact initial EMA/official Tiny
identity and its actual source-archive digest.

Independently verify step20,000, all91 finite model/EMA tensors and89 finite
Adam states whose counters are20,000. The resolved architecture matches V102.
Every archived Python module matches the original plan, and the complete
source archive digest is recomputed. The actual training manifest SHA remains
`a68450954e5ed7a1c45da3349c7007faf3a608c9b8a4dd3fb1c16f3882ce277b`.
Preserve a read-only canonical exact copy at
`/mnt/external/demosaic/models/v104-final20000.pt`, SHA256
`8a3a7d94f2b1465cbdddbeec201fb37a2f69b12c74f9298527a94e3a7bbf6300`.
[Original20k boundary/source evidence](../docs/results/V104-original20000-training-boundary-v1.json).

The original CPU report completes all12 fixed material cases, comparing final
V102/V104 EMAs. A source-frozen gallery worker waits for its exact original
owner to exit, then constructs all three native comparison boards with the
existing RawNIND crops. All12 parent scores and triplet PNGs reproduce the
earlier V102 report exactly. All12 original RawNIND observation archives also
match current arrays exactly by dtype and value. Noisy/GT pixels, coordinates,
conditioning and display settings agree across methods. No inference is
repeated for the gallery and no crop pixels are resized.

All60 native cells in the three20-cell boards were actually viewed at original
resolution. V104 remains visually close to V102, with slightly more coherent
low-noise bark/canopy structure. White plumage, distant canopy and individual
hairs remain soft at high noise. Both learned models retain substantially
more structure than RawNIND on these cases.

Four-source sRGB PSNR means, V102→V104:

| Condition | V102 | V104 | Difference,dB |
| --- | ---: | ---: | ---: |
| ADC-only |39.24687|39.49290|+.24604|
| ISO100 prior |40.63881|40.80494|+.16612|
| ISO12800 prior |33.46901|33.49300|+.02399|

PSNR, SSIM and gradient error improve in12/12 cases. Chroma improves in11/12,
with a5.92e-6 increase on high-noise fur. All four exact source IDs remain
outside the actual training manifest. These are four selected source-held-out
contexts, one noise draw per condition and RGGB, rather than the full427,
measured-camera or real-GFX result. Additional training, seed and corpus change
together, so the gain does not isolate a data effect.
[Complete selected-material receipt](../docs/results/V104-final20000-heldout-detail-CPU-v1.json).

Publish immutable V102/V104/RawNIND boards and native triplets under
`docs/images/detail-v102-v104/`, preserving earlier galleries and receipts.
The README now shows two V104 noisy/restored/exact-synthetic-GT triplets and
labels their scope; its real GFX triplets retain completed V102 full-frame
outputs. Update the current guides from “training” to the completed20k and
active quality evaluation. V102 remains the fully evaluated overall reference
while the new broad results run; useful V104 gains are documented immediately.

The original full photographic/camera/texture/color/GFX/highlight evaluation
and subsequent complete102MP RGB16 exports continue through their existing
queues. Their results will inform the next useful baseline and initializer
for the cleaned90,864-source Tiny/Small trial. No broad quality, state-of-the-art
or100MP/10s conclusion is drawn from this selected material result. The full
project goal remains active.

Final publication verification passes: 82 receipt reference entries, 121 unique
file hashes, all 36 native triplet PNG hashes, five unchanged original plans
and 473 local links across the 16 changed/new Markdown files. The feature
branch tip `4381fc2` remains an ancestor of main through merge `12f0810`.
