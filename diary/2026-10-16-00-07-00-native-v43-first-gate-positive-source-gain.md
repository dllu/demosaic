# V43 first-gate review complete; broader native corpus retained

The private807d929 controller completed at2026-10-16 06:59:03UTC. All33 shared
logged Commons/paired observations match V37/V39. Source bundle
`c758d2b56213869607fd3097936fae6cacf0e6a1f2a79ff9dea5b40c5d971bac`.
Checkpoint SHA
`8ee3e960acdf95d88ba06eab30ac9abbab8bab28b0dc63d79b304a960eb535c5`.
Same immutable V34 EMA, seed47, B16, freshAdamW/EMA, LR3e-5/planned3000,
full-resolution/precision and other data as V37/V39. Only native selection
changes53/31 ->128 captures/106 declared groups, preserving all legacy/prior
sources and adding69 reviewed CC0 photographs. No current inference-export
precision policy is silently applied to training/evaluation.

V43 known primary54.26354/AHD RGB40.02047/SSIM.930380; unseen
53.72974/38.56632/.922620. V43−V37 unseen primary+.04984dB, source95%interval
[+.00316,+.09566]; V43−V39+.02052[+.00433,+.03742]. Known−V37 is−.01590 with
interval crossingzero. V34 parent retains a higher unseen primary mean:
V43−V34−.05690[−.17569,+.04877]. No claim that every metric improves.

Full427 photo34.70399/.955576 versus V37 34.65497/.955273 and V39
34.66049/.955174. Photo gains+.04902dB overV37[+.03872,+.05855] and+.04349
overV39[+.03110,+.05718]. Procedural33.85008/.967898: small positive means,
wide interval crossingzero versusV37. These source intervals do not measure
seed variance/convergence. Unseen auxiliary RGB/SSIM roughly tie the strongest
channel-calibrated RawNIND; a broad qualitative margin remains unproven.

The larger native corpus becomes the next full-resolution training recipe.
V43 becomes the current experimental reference based on photo/rendered means
and the matched-data gains; its parent-primary tradeoff remains explicit.
Selected GFX foliage/fence look close toV37; fine foliage/fabric remains too
soft. README now shows V43's two native exact-synthetic-GT triplets plus the
standing GFX foliage/fence, with accurate ISO100 reference labels. A stable
versioned inference alias `/mnt/external/demosaic/models/v43-first1000.pt`
points to the immutable known-evaluation weight snapshot, SHA verified. The
README CLI example uses it with evaluated tile512/overlap64/FP16 settings.

Ten new native160px triplets pass PNG SHA, dimensions, shared metadata and
exact noisy/reference panel checks. Real AHD and separateISO100 references are
not exactRGBGT. Two complete8746×11662 RGB16/ICC outputs pass SHA/size, actual
dtype/shape/bit-depth and sampled-code checks. GFX restoration34.97s is a
successive shared-machine observation, not a controlled speed comparison or a
10-second result. Cached V34/V37/V39/RawNIND are reused only after identical
data/render/metric/evaluator protocol and exact24/30 real classical summaries
plus37,212 synthetic classical case records. Combined synthetic111,636 cases.

Full report `docs/native-v43-1k-review.md`, receipt
`docs/results/native-v43-1k-review.json`. Publication scripts are archived in
`/mnt/external/demosaic/runs/`. All343 tests passed in27.49s; Ruff passed.
No owned training/evaluation process remains active; Commons download continues.
First-gate artifacts are frozen before any continuation.

The next useful quality gate is a matched continuation of V37/V39/V43 to
step2000, preserving each original optimizer/RNG/source snapshot and planned
3000 schedule. Inspect the older private worktree/runtime identities before
launching, preserve these immutable first-gate snapshots and compare actual
shared logged observations. Current-architecture trained DINO ablation,
protected-final assessment, decisive RawNIND/SOTA quality and the10-second
target remain unproven. The objective remains active.
