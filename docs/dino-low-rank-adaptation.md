# Optional DINO feature adaptation

`model.dino_lora_rank: 4` enables a small training experiment that adapts DINO's
attention to noisy RAW previews. The current model keeps its original pretrained
DINO tensors fixed and learns only its feature projection/gate. This option also
learns low-rank changes to the foundation model's attention query/value matrices.
**It passes CPU/GPU execution checks; it is not quality-trained or selected.**
Existing checkpoints and recipes default to rank0 and keep their original path.
Running private corpus/throughput workflows use their frozen source unchanged.

The construction follows [LoRA](https://arxiv.org/abs/2106.09685):
`W_effective = W_pretrained + B @ A`, with random A, initially zero B and unit
scale (alpha=rank). Applying it to queries and values in all12 pinned DINOv3-S
blocks adds73,728 trainable parameters at rank4, about0.34% of the21.6M foundation
parameters. This transfers an existing adaptation method to our restoration
context; the source paper does not establish RAW restoration gains.
[Official DINOv3](https://github.com/facebookresearch/dinov3) and the
[Transformers interface](https://huggingface.co/docs/transformers/model_doc/dinov3)
remain the backbone sources. No upstream LoRA implementation is copied.

The original backbone weights remain frozen and use the existing pinned revision
`114c1379950215c8b35dfcd4e90a5c251dde0d32`. Autograd traverses its operations when
adapters are enabled, so those new parameters can learn. The backbone remains
in evaluation mode, retaining deterministic foundation behavior. Rank0 keeps
its original no-gradient backbone execution. The RAW/physical feature and
native-output precision policies remain the same.

PyTorch weight parametrizations attach the updates to the pinned ViT q/v
projections. The same adapter modules are registered under `context.lora` for
portable saving: original `context.backbone` tensors are deliberately omitted
from restoration checkpoints, and saving adapters only there would lose them.
Optimizer traversal deduplicates the shared parameter objects. The loader
requires every external adapter tensor; a missing learned tensor is an error.
Invalid rank, absent DINO, unsupported projection layouts and repeated target
installation are rejected.

CPU tests use a small actual Transformers DINOv3 architecture to check:

- Exact initial context-feature equality with nonzero fusion gates.
- Finite adapter gradients, second-step gradients to both factors and unchanged
  original foundation weights.
- Nonzero adapter persistence through portable restoration checkpoint loading,
  and rejection of a missing learned matrix.
- Uninterrupted versus interrupted/resumed training, including optimizer, EMA
  and RNG state.

A separate [genuine pinned-weight preflight](results/dino-lora-cpu-preflight-v1.json)
loads V43's learned projection/gate and compares frozen versus rank4 contexts.
Initial FP32 predictions match exactly. A single synthetic RGB gradient fixture
produces nonzero B gradients while all original foundation tensors remain
unchanged; saved nonzero updates reproduce exactly after reloading. All24
projections and73,728 new parameters are verified. The fixture is not a trained
restoration checkpoint. It uses no personal or protected image gradients.

The CPU regression run passes343 tests with eight CUDA tests skipped; all nine
dedicated adapter tests pass, including the subsequently added training-resume
check. The complete CUDA suite now passes **352 tests in 30.78 s**. The
[genuine full-model GPU preflight](results/dino-lora-gpu-preflight-v1.json)
preserves exact initial predictions under both BF16 and FP16 on all four CFAs,
with FP32 output. LoRA receives finite nonzero gradients and original foundation
tensors remain unchanged. A four-update training fixture preserves complete
AdamW state through step2 → step4 resume; all48 learned matrices are saved and
EMA tensors reload exactly. Those few updates verify execution, not quality.

The checks ran in the frozen ca846a0 checkout after the owned current-pipeline
batch sweep completed and exited. Source/config/checkpoint/script and regression
log hashes remain in the receipts. Neither these fixtures nor their small-patch
allocation measurements establish full-batch throughput or restoration quality.
The corpus review selected V43 step2000 as the photographic reference; its
first1000 alias remains fixed for reproduction.

A matched rank0/rank4 quality trial should use one reviewed
parent with fresh AdamW/EMA and identical per-step data, LR and update budget.
Preserve all common parent tensors and verify zero-update predictions before
training. Publish complete known/unseen and427-photo/16-procedural results,
full102MP GFX outputs, native exact-GT triplets and accurately labeled real
references before selecting it. Extra backward activations and effective-weight
construction have unmeasured costs. The separate
[fresh DINO presence/absence comparison](fresh-dino-ablation.md) remains useful
for attributing the foundation branch's contribution itself.

The first [matched quality trial, V49](dino-lora-v49-review.md), is complete
against V47 with exact source/initial tensors and all41 shared seed50
observations. It loses unseen primary/photo PSNR and stops at1000; no promotion.
