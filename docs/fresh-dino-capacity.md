# Fresh DINO capacity comparison with matched arithmetic

The next quality experiment compares no context, frozen DINOv3-S/16 and frozen
DINOv3-B/16 in the current full-resolution RGB architecture. All start from
the same verified Gaussian restoration weights, with zero measurement/camera
projection and zero context gate. There is no inherited JDD/DINO restoration
history. This addresses both the missing current-architecture DINO ablation and
whether larger frozen features help. **Preflights pass; trained quality remains
unproven.**

| Recipe | Frozen foundation parameters | Trainable parameters | Context feature width |
| --- | ---: | ---: | ---: |
| [V45 no context](../configs/control-anchored-native-fresh-b16-v45.yaml) | 0 | 32,642,368 | 0 |
| [V44 ViT-S](../configs/dino-anchored-native-fresh-b16-v44.yaml) | 21,596,544 | 33,233,216 | 384 |
| [V51 ViT-B](../configs/dino-base-anchored-native-fresh-b16-v51.yaml) | 85,660,416 | 33,823,040 | 768 |

S/B differ in frozen features and the matching adapter input width; this does
not isolate feature quality from adapter width. All66 common CNN tensors match,
SHA256 `c7ebf6c7c99306601c08698505276061ef8055218bfcfb65d19c8302929bf21b`.
All use seed48, B16, LR1e-4/planned10000 and a first review after1000 updates.
The fixed40170-source Commons4/native128/paired32 recipe,25/25/50 mix,
pre-reduction geometry/PSF, original8× validation and full-resolution/physical
precision remain common. V50 separately tested the larger corpus; this experiment
keeps the established corpus fixed to isolate the branch/capacity change.

## An arithmetic confound found before training

The [legacy CPU diagnosis](results/fresh-dino-middle-precision-diagnosis-v1.json)
finds that a zero DINO offset promotes the deep skip from BF16 toFP32. Without
context, the same skip stays BF16. A genuine fresh one-CFA/native32 fixture is
exact in CPUFP32 but differs by maximum.00114676 under CPUBF16. Thus earlier
CPU-FP32 initialization equality alone did not establish mixed-precision parity.
V47/V49/V50 all have context and share the same arithmetic; this confound is in
the proposed fresh presence/absence comparison.

`model.rgb_middle_skip_fp32` explicitly promotes that skip for all fresh arms;
the convolutions still follow AMP. Original DINO arithmetic is retained and the
absent branch receives the same numerical policy. The default is false, with
no added state tensors or parameter changes, preserving older checkpoints and
their existing inference path. Only prepared, previously untrained V44/V45/V51
recipes enable it. Six targeted tests verify BF16 value/input/weight-gradient
equality for absent/zero context, legacy defaults, unchanged existing FP32
offset behavior, checkpoint round trips and invalid-backbone rejection. The
complete CUDA-enabled suite passes379 tests in40.18s.

## Genuine-weight preflights

[CPUv2](results/fresh-dino-capacity-cpu-v2.json) checks12 combinations of two
native shapes, three noise priors and FP32/BF16 for all four CFAs, with exact
initial outputs across all arms. CUDA is not initialized. V1 is retained as
historical FP32-only evidence.

[CUDAv1](results/fresh-dino-capacity-gpu-v1.json) verifies exact initial outputs
at all four CFAs/three priors in FP32/BF16/FP16. Each arm then performs two
discarded BF16 AdamW updates at actual batch16/native256. Gradients are finite;
context gates and, on the second update, adapters receive nonzero gradients.
Original S/B foundation hashes remain unchanged. Portable checkpoints preserve
the policy and reload with exact FP16 predictions. Peak allocation ranges
6.38–6.74GB across these fixtures; this is not a repeated throughput comparison.
Source/config/initializer/checkpoint/driver hashes and snapshots are archived.

The [official ViT-B card](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m)
describes a general dense-feature model, not RAW-restoration results. Approved
genuine weights are pinned to `5931719e67bbdb9737e363e781fb0c67687896bc`, with
LFS SHA256 verification; S retains its original pinned revision. No foundation
substitution, random fallback or low-rank adaptation is used.

Run sequentially in frozen source, require all41 logged observations to match,
and review equal optimizer updates. Include known/unseen paired data, full427
photos/16 procedural sources, exact-GT native triplets and the full102MP GFX
sky/building/foliage/fence scene with verified RGB16 outputs. Add the existing
RawNIND calibration variants as direct comparators. An early gate is not
convergence or SOTA. Current V43/README aliases stay fixed until the complete
trained comparison supports a selection; protected-final scoring remains closed.

The [sequential workflow is now live](results/fresh-dino-capacity-launch.json)
in frozen `8580a4e`: no-context first, S next, B last. The first arm reports
finite losses with verified Gaussian-only lineage and the explicit precision
policy. RawNIND source/weight hashes and fixed manifest hashes are bound in the
plan. Trained results and cross-arm data equality are still pending.
