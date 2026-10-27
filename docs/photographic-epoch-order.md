# Photographic epochs at a fixed training budget

**An optional deterministic epoch order visits all 90,778 prepared training
photos within 20,000 updates, versus 62,873 (69.26%) with replacement.** It
changes ordinary photographic identities while retaining the same domain,
procedural and reviewed-region choices. This is a verified data-pipeline option;
its restoration-quality effect is unmeasured. Earlier trials keep their frozen
inputs. The new [V134/V135 comparison](photo-epoch-training.md) has all four real
CPU/CUDA checks complete and queues matched 20k replacement/epoch training.

[Full actual-reader audit, source bindings and tests](results/photo-epoch-order-v1.json) ·
[Cumulative source coverage](results/photo-epoch-order-coverage-v1.csv) ·
[Preview recipe](../configs/photo-epoch-order90778-preview-v1.yaml).

## Fixed schedule and result

The prospective schedule uses the prepared 90,778-photo/33-region set, seed 70,
20k updates, B16, paired/native fractions .25/.25, flat/synthetic fractions .10/.20
and a 5% reviewed quota conditional on photographs. It is not a new trained
model or a comparison against different corpus membership. Both order policies
below use this exact cohort and the same global sample indices.

| Quantity | With replacement | Epoch order |
| --- | ---: | ---: |
| Commons / native / paired steps | 10,046 / 4,965 / 4,989 | Same |
| Ordinary / reviewed / procedural Commons draws | 106,823 / 5,601 / 48,312 | Same |
| Unique training photo IDs visited | 62,873 | **90,778** |
| Available photos visited | 69.26% | **100%** |
| First complete ordinary-photo epoch | — | Step **17,039** |
| Ordinary-photo visits per source | Varies; some never visited | 74,733 once; 16,045 twice |

Only ordinary-photo draws advance an epoch. Each epoch independently shuffles
the exact ordered active training rows; the 16,045-draw partial second epoch has
no repeats. Reviewed regions retain their independent quota and may also appear
through ordinary sampling. At larger reviewed quotas or shorter budgets there
may be too few ordinary draws to cover the corpus. Coverage here does not prove
more useful detail, a better loss trajectory or higher PSNR.

## Preparation and use

The preview recipe describes source selection only; it has no model or run
directory. Generate a new order into an unused destination:

```bash
PYTHONPATH=src:scripts uv run python scripts/prepare_photo_epoch_order.py \
  configs/photo-epoch-order90778-preview-v1.yaml .cache/photo-order-preview
```

The preparer validates the reviewed catalogue and its caches, then enumerates
selection metadata without calling `__getitem__`, augmenting targets or
generating observations. It saves a JSON header and an int32 array mapping global
indices to active row positions. Non-Commons, procedural and reviewed slots use
−1. Actual training looks up only ordinary-photo entries; an unplanned entry
fails rather than silently falling back to replacement sampling.

A future training recipe with identical source/selection/layout fields can set
`photo_epoch_order` to the header and pin its printed
`photo_epoch_order_sha256`. The prepared local proof header is
`.cache/current-quality-20261023-v1/photo-epoch-order-90778-v1/prepared-v1/photo-epoch-order.json`,
SHA256 `d7ab526c18ca9724c8a580e3baff7cb4beac3e238749d173992d332bdfe05633`.
The array has 320,000 entries (1.28 MB plus its small NPY header).

The reader checks the manifest, ordered training IDs, seed, family fractions,
reviewed quota/catalogue, payload hash, dtype and bounds. Training additionally
checks batch size, domain fractions, single-group layout and the full horizon.
Changing the frozen header on resume is rejected before model construction.
Checkpoints preserve the header and payload in their source snapshot. Workers
and resumed loaders use the same stateless global-index lookup.

Each discarded CPU/CUDA check needs its own order matching its exact recipe;
a production B16 order cannot be reused with a B1 check. The
[matched training runner](photo-epoch-training.md) prepares separate CPU orders
and queues production after V133's original training and automated review exit.
No existing trial's source inputs or budget are changed.

## Verification

The audit follows all 160,736 Commons slots through both the actual new reader
and the original frozen pre-change reader, stopping before source pixels or
procedural generation: **321,472 real selection-path calls**. An independent
domain calculation matches every one of 20k steps. Photographic IDs match the
saved order; every complete epoch contains all active sources exactly once.
All procedural/reviewed selections and their local RNG states match.

An additional **88 actual clean reads** compare unchanged default behavior with
the frozen reader, exercise the new procedural/reviewed paths and load four
newly ordered ordinary targets. **10,223,616 common FP32 values match exactly**;
ordinary draws open only their selected cache. Python/NumPy/Torch RNG states
remain unchanged and CUDA stays uninitialized. This audit performs no neural,
sensor-noise, RAW or optimizer work; it does not visually certify every corpus
source. The existing source-review ledger remains at 1,919 inspected IDs.

The original focused suite passed **83 tests**, including an actual tiny-model
uninterrupted/resumed training comparison, source-snapshot payload equality and
changed-order rejection before construction. These unit tests use their own
small fixtures; no production model is trained or re-evaluated. Ruff passes.

Implementation: [Bound order and resume guard](../src/demosaic/photo_epoch_order.py) ·
[Preparation tool](../scripts/prepare_photo_epoch_order.py) ·
[Reader integration](../src/demosaic/data.py) · [Training integration](../src/demosaic/train.py).
