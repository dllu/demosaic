# Fresh DINO comparison for the current pipeline

V44 and V45 are prepared recipes for a matched training comparison of DINOv3
context in the current full-resolution pretrained RGB architecture. **Training
has not started.** The V37/V39/V43 corpus continuation and its complete review
finish first. Earlier DINO ablations used a different restoration architecture;
turning context off only at inference also changes the input distribution of
an already trained network.

Both new arms start from the same verified original Gaussian RGB restoration
weights and zero measurement/camera projection. They inherit no prior JDD
checkpoint. V44 adds the pinned frozen DINOv3-S/16, its trainable adapter and a
zero fusion gate. V45 omits that context branch. All 66 shared state tensors
match exactly. Four initial CPU FP32 predictions, one for each CFA, also match
exactly on the recorded 32px fixture with explicit shot/read conditioning.
These are execution and initialization checks, not measured quality gains.

The [preflight receipt](results/fresh-dino-ablation-preflight.json) records
configuration and source hashes, the common tensor digest, pretrained lineage,
parameter counts and CPU fixture. Reproduce it with:

```bash
source scripts/env.sh
uv run --no-sync python scripts/preflight_fresh_dino_ablation.py
```

The recipes differ only in run destination and `model.dino`:

- [V44 with DINO](../configs/dino-anchored-native-fresh-b16-v44.yaml)
- [V45 without DINO](../configs/control-anchored-native-fresh-b16-v45.yaml)

Both use seed 48, batch 16, fresh AdamW/EMA, base LR 1e-4, a planned 10,000-update
schedule and a first review at 1,000 updates. The larger initial LR follows the
fresh pretrained-RGB setup rather than the smaller continuation LR. The mix
stays 50% Commons/procedural, 25% paired RAW and 25% native RAW, using the same
complete frozen Commons4, reviewed native128 and original8 validation as V43.
Geometry/PSF runs before final area2; GAT, physical anchors, full-resolution CNN
and original arithmetic remain fixed. Per-step data RNG isolates the selected
observations from model initialization. Every logged input/target fingerprint
must match across the two arms.

Run sequentially in a frozen source checkout, retaining the first gate:

```bash
uv run --no-sync demosaic train configs/dino-anchored-native-fresh-b16-v44.yaml --stop-after 1000
uv run --no-sync demosaic train configs/control-anchored-native-fresh-b16-v45.yaml --stop-after 1000
```

Review known/unseen paired development, the complete 427-photo/16-procedural
suite and full102MP GFX before extending either arm. Publish at least two
native exact-synthetic-GT triplets per checkpoint and all standing GFX regions,
with common source/ROI/noise/display settings and accurate real-reference
labels. Compare equal optimizer updates and equal observations; report measured
runtime separately because omitting DINO reduces computation. One seed and an
early gate do not establish convergence, a universal DINO effect or SOTA.

Protected-final, GFX and scene siblings remain outside training. The current
V43 reference and its immutable first1000 alias remain unchanged.
