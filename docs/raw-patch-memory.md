# Neighboring gradient descriptors before global memory

**V140 adds a learned neighborhood descriptor to the memory-only RAW branch.**
Genuine CPU/CUDA16+2 checks pass, with91 parent tensors exact in model and EMA.
A fresh1,000-update run waits for V139's original numeric/native/faint/JPEG
review. Restoration quality remains unmeasured; V120 stays the general choice.
Its matched102-input native/faint/GFX review is queued after that training.

[Implementation](../src/demosaic/raw_patch_memory_features.py) ·
[Tests](../tests/test_raw_patch_memory_features.py) ·
[Recipe](../configs/quality-v120-raw-patch-memory-pilot-v140.yaml) ·
[Check driver](../scripts/check_raw_patch_memory_pilot.py) ·
[Training queue](../scripts/train_patch_memory_pilot.py) ·
[Checks and training evidence](results/raw-patch-memory-checks-v1.json) ·
[Review controller](../scripts/review_patch_memory_pilot.py) ·
[Endpoint/control binder](../scripts/bind_patch_memory_review.py) ·
[Review queue and preflight evidence](results/raw-patch-memory-review-queue-v1.json).

## The hypothesis and operator

[V139](raw-global-memory-only.md) embeds each packed pixel's eight signed
horizontal/vertical phase differences independently before global matching.
It supplies no descriptor of neighboring gradient arrangements at that stage.
Repeated fine structure may benefit from comparing those arrangements rather
than individual noisy vectors. This is a hypothesis, not an established cause
of real mesh loss; V139's pending quality result remains separate evidence.

V140 retains the point embedding and adds a zero-initialized64→32 projection
of eight neighboring vectors. Each neighbor retains all eight gradient channels;
the center is excluded. Fixed row-major coordinates use zero padding outside,
without border wrap or interpolation. These are3×3 neighborhoods of gradient
vectors on the packed CFA grid, not3×3 native RGB pixels. Variance/CFA conditions,
64 slots, four cosine-attention heads and image-scale normalization stay unchanged.

```mermaid
flowchart LR
    R[Four-phase signed differences] --> P[Existing point embedding]
    R --> N[Eight neighboring gradient vectors]
    N --> Z[Zero-initialized 64-to-32 projection]
    P --> S[Add descriptors]
    Z --> S
    S --> M[Memory read and write attention]
    M --> O[Existing phase shuffle and zero projection]
    O --> C[Frozen parent RGB trunk]
    D[Existing frozen DINOv3 pyramid] --> C
```

Every returned feature still passes through both attention operations. There
is no local bypass to the stem. The fifteen shared initial tensors remain exact;
one new tensor adds **2,048 parameters**, for16 tensors/16,192 parameters overall.
Initial descriptors equal V139's point descriptors, and the zero final projection
preserves the parent output. Constructor RNG is preserved. Bias-free values and
signed differences keep per-phase spatial constants exactly zero after learning,
including spatially varying variance. Noisy flats and camera color still need review.

## Configuration and compatibility

```yaml
raw_global_only: true
model:
  raw_global_features: true
  raw_global_conditioning: patch-memory-v4
```

The complete recipe selects native anchored/stabilized RGB and official frozen
DINOv3 ConvNeXt-Small. Missing mode remains `legacy-v1`; `cosine-rms-v2` and
`memory-only-v3` keep their operators/state layouts. Changed modes reject before
resume construction; strict loading requires V140's learned patch tensor.

The common forward now calls a point-embedding hook. Independent AST inlining
reproduces the entire previous forward exactly. Of68 earlier neural modules,65
remain byte-identical; other changes are limited to selecting constructors and
explicit mode/hook code. The new snapshot has69 modules. Existing jobs retain
their original frozen sources/plans.

## Actual implementation checks

Both checks start freshly from V12020k and keep the1k horizon while running16
updates plus a genuine two-update resume. CPU uses native128/B1/FP32; CUDA uses
256/B16/BF16 with physical/feature math in FP32. Only16 branch tensors train;
all91 parent tensors remain exact in both model and EMA at16 and18. All107
model/EMA tensors and16 Adam states are finite. Eight changed-mode/scope resumes
per device reject before model construction.

All36 clean/noisy hashes match saved V137. Independent checking compares
162,944,388 prepared-array values and rehashes all36 batches. Initial RGB/auxiliary
outputs match4,259,840 values exactly, without control inference. All16 parameter
tensors receive finite nonzero gradients; all2,048 patch weights become nonzero
in every saved16/18 state. The audit checks263,496,816 finite saved values and576
gradient metadata fields with neural module calls forbidden. It does not
independently rederive backward derivatives.

Across the two genuine checks:36 root/encoder/optimizer calls and306 prepared
target slots, not distinct photographs. Initial branch offsets contain68,157,440
exact zeros. CUDA peak is7,995,275,776 bytes under12GiB. New CUDA admission is
50GiB, CPU40GiB, runtime floor32GB and checks30min each. Existing52GiB policies
stay unchanged. Concurrent-workload timings are not speed measurements.

The99-test feature/scope suite and21 new handoff tests pass: independent NumPy
coordinate/projection arithmetic, spatial arrangement, no center/border leakage,
all-CFA constants, tiny/rectangular inputs, batching/layout, gradients, strict
reload, mode guards and complete dependency handoff. A test-collection filename
typo collected zero tests; a static-audit metadata helper initially rejected a
string path after its source assertions passed. Both are preserved. Neither
required training-check or old-control replay.

## Queued quality experiment

V140 changes only the descriptor against V139's recipe: V120 parent,
90,782 photos/27 regions, seed70,50% reviewed quota, paired32/native128, zero PSF,
native256/B16/BF16, single-view loss, LR1e−3 and100-step warmup. The newer90,774/36
prepared bank remains separate. Checks end during warmup and do not establish
convergence or peak-LR behavior.

The controller adopts byte-identical completed checks and starts production
freshly from V120. It waits for all seven original V139 review stages and exact
owner exit within that queue's original deadline, without a quality-score or
human-publication gate. Then50GiB RAM and128/208GiB internal/external space must
hold15s within a2h wait;12GiB CUDA cap,32GB floor and8h worker limit apply. No
original job, data, budget or deadline changes; no automatic retry/horizon reset.
The run plans1,000 root/optimizer plus64 validation and1,064 encoder calls over
16,000 target slots. All input hashes must match saved V137.

The dedicated review controller is live and waiting for the original V140
training owner to finish. It keeps the fixed102 future calls:64 shadow,16 ordinary,
16 faint ADC, four main-GFX512 contexts and two extra-mesh768 profiles. It adopts
612 predictions from six old methods, including V139 and its inherited V138
controls. Before inference, it checks the actual1k state/source and all1,000
V139 clean/noisy hashes, as well as saved V137 hashes. The V139 final primary,
faint and JPEG review must be complete with its exact owner exited.

The binder preserves all observation fields and the original four-control prefix,
adopts V138 from V139's executed plan, then adds V139 predictions. This matters
because V139's prospective queue has four controls while its executed plan will
have five. The first preflight caught V120's legacy mesh label/checkpoint format
before any Torch import. A corrected binder also accepts that exact saved format
and nearby-profile suffix; it does not rewrite the old controls. The first
unlaunched queue/binder and failed preflight remain preserved. The live queue is
`queue-plan-v2.json`; no completed inference or controller was restarted.

All69 neural modules equal the training snapshot; collector, reporter, independent
auditor and both faint operators are unchanged. The corrected preflight verifies
all102 records and408 existing predictions, exercises204 explicitly simulated
future bindings, and rejects the live incomplete training before importing Torch.
It is wiring evidence, not proof of future predictions or rendering. The38 new
review-handoff tests plus21 original training-handoff tests pass.

Primary support is672 metric rows/168 groups/64 native PNGs with29,491,200 RGB
channels. The seven-method faint supplement covers420 strata/224 decompositions
and four nine-cell boards. Four additional mesh boards compare noisy/V120/V139/
V140 with both camera JPEGs and corrected DSCF3835 ISO100/AHD. Source-defined masks,
ROIs, noise and display exposure stay fixed. Exact synthetic targets receive
native100% noisy/denoised/GT triplets; binned and independently captured references
retain their approximate labels. Both protected GFX pairs and both mesh profiles
are included without new RAW decoding or noise generation.

New review admission is50GiB for CUDA and40GiB for CPU, with12GiB CUDA allocation
and32GiB runtime RAM reserve. Each stage has a2h headroom wait, collection has1h,
and CPU stages have30min. Its new absolute deadline is V139's original quality
deadline plus24h. All earlier plans/deadlines and V140's1k training queue remain
unchanged. Numeric/native-pixel audits and actual viewing/publication are still
required; the queue establishes no restoration gains, full427-photo/camera/color
quality, tiled seams/full frames, speed or broad superiority.
