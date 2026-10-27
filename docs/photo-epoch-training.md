# Cleaned-corpus training and photographic epochs

**V134/V135 have passed all four real CPU/CUDA checks. Fresh 20k production
runs and full endpoint reviews are queued; restoration quality is unmeasured.**
Both use the cleaned 90,778-photo/33-region corpus and V120 Small architecture.
V134 samples ordinary photos with replacement; V135 uses the
[audited epoch order](photographic-epoch-order.md). V120 remains the general
recommendation. The parent is fixed for this controlled comparison; the current
recommendation can advance independently as other experiments show useful gains.

[Recipes: V134](../configs/quality-v120-photo-epoch-v134.yaml) ·
[V135](../configs/quality-v120-photo-epoch-v135.yaml) ·
[Actual checks, frozen plans and queued reviews](results/photo-epoch-training-setup-v1.json).

## What the comparison tests

| Setting | V134 | V135 |
| --- | --- | --- |
| Parent | V120 Small EMA, step 20,000 | Same |
| Commons sources / reviewed regions | 90,778 / 33 | Same |
| Ordinary photographic sampling | With replacement | Independent shuffled epochs |
| Reviewed quota within photographs | 5% | Same |
| Unique photos in the planned 20k schedule | 62,873 (69.26%) | 90,778 (100%) |
| Seed / updates / native patch / batch | 70 / 20,000 / 256 / 16 | Same |
| Precision / sensor views / optical PSFs | BF16 / one / zero | Same |
| LR / warmup / cosine horizon | 1e−5 / 100 / 20,000 | Same |

Both retain V120's pretrained DRUNet RGB trunk and official frozen DINOv3
ConvNeXt-Small pyramid, sensor-valid camera supervision, corrected paired32 and
native128 catalogues, bin4 → geometry → area2, and photographic contrast
attenuation probability .25. Shadow, normalized-band, conditional-mean and DINO
feature-loss additions remain off. Source order is the sole difference between
the two recipes. Source coverage alone does not establish better reconstruction.

The original V133 uses 90,781 photos/29 regions. V134 is a new cleaned-data
control, incorporating three later exclusions and four material annotations;
its comparison with saved V133 results measures that combined data change.
V135 versus V134 isolates ordinary-photo ordering on identical membership and
annotations. Existing controls are reused rather than retrained or re-evaluated.
Both private GFX pairs, their JPEGs and siblings remain held out.

## Genuine implementation checks

Each arm completed 16 fresh updates followed by two valid resumed updates on
CPU128/B1/FP32 and CUDA256/B16/BF16. The step-16 checkpoints remain intact. All
four runs used the original 20k horizon; no schedule was restarted or extended.
Changed order mode and changed hash/binding resumes were rejected before model
construction in all eight probes.

The checks executed **72 root forwards, 72 encoder forwards and 72 optimizer
updates on 612 target slots**.
Each model/EMA has 91 restoration tensors and each optimizer has 89 states at
step 18. The official encoder remains unchanged and frozen. CUDA peaks were
7,041,804,800 bytes per arm. V135's hook compares unaffected prepared values
against V134 before its model calls:

| Device | Unaffected example slots | Exact prepared values | Exact native/paired batches |
| --- | ---: | ---: | ---: |
| CPU | 13 | 1,851,626 | 9 |
| CUDA | 196 | 112,201,160 | 9 |

An independent NumPy pass inspects all eight retained step-16/18 states:
**1,052,951,336 finite values**, with correct tensor/state counts and Adam steps.
The full-endpoint verifier rejects both genuine 18-step candidates before
neural construction. It does not relabel them as completed models. Four
validation-reader comparisons additionally match 786,432 FP32 target values
against the original frozen reader, with unchanged RNG and no new observations.
The source/collector and independent metric checks introduce no neural calls.

The focused suite passes **148 tests**, including resume/source-order contracts,
old queue behavior, saved-control adoption and strict full-frame comparisons.
Ruff passes. Toy-model unit tests are separate from the actual DINO checks.

## Production and endpoint review

Production waits for the exact original V133 training controller and automated
endpoint/green-mesh review owner to complete and exit, protecting their memory
headroom. CPU checks require 40 GiB available RAM; CUDA checks/production require
52 GiB. The runtime floor is 32 GB and CUDA allocator cap 16 GiB. Limits remain
30 minutes per check, 48 hours per production worker and eight days for admission.
Failures retain artifacts and stop; there are no automatic retries or resets.

Each arm starts freshly from the same V120 EMA for **20,000 updates**, with
640 validation and 20,640 encoder forwards. Step-1000 progress is retained within
that same horizon. The worker enforces all native/paired input fingerprints and
the first 18 unaffected example arrays against V134.

Four live endpoint queues cover the full photo/known-unseen CFA/texture/color
panels, six main GFX regions, highlights and complete 102MP linear/sRGB RGB16
exports. Independent archive reduction and native comparison rendering follow.
They plan **9,176 new root/encoder calls** in total, including four CPU mesh calls;
no quality calls have run yet. V120/V117 controls are retained, and original V133
results are adopted when complete. V133/V134/V135 comparisons require the same
32px full-frame grid and all 130 actual tile-input fingerprints to match.

Reports include native noisy/restored/exact synthetic GT triplets and both real
GFX pairs. The extra mesh uses DSCF3842 ISO6400 / corrected DSCF3835 ISO100 under
both fixed profiles; nine existing/deferred mesh predictions are reused.
ISO100/AHD and camera JPEG references differ in aperture, exposure and moving
subjects and remain explicitly **not exact GT**. Actual image review and measured
strengths/weaknesses will guide documentation and model choices.

Local roots under `.cache/current-quality-20261023-v1/`:

- `photo-epoch-training-v1/run`
- `V134-V135-photo-epoch-quality-v1`
- `V134-V135-photo-epoch-independent-audit-v1`
- `V134-V135-photo-epoch-comparisons-v1`
- `V134-V135-photo-epoch-green-mesh-v1`

[Training runner](../scripts/train_photo_epoch_trial.py) ·
[Local-time history](../diary/2026-10-27-11-53-51-photographic-epoch-training.md).
