# Whole-scene context: implementation and next quality test

The user's sky-versus-fence example identifies a missing input. The
[production/context review](weak-detail-global-context-production-review-2026-11-16.md)
proposes the right next architecture experiment: preserve local RAW reconstruction
and the existing local DINO encoder, then add one spatial scene encoding shared
by native tiles. The review's historical evidence cutoff remains unchanged.

Current code still sends DINO only the current tile: `inference.py` passes no
scene preview or tile box, and `pretrained_rgb.py` calls its context encoder on
the locally rendered RGB. The recent full guided/fine studies use512/768-native
contexts, not the whole photograph. Their useful response and cab-tint gains
still leave weak crossings missing, with increment/colour costs. See the
[completed full guided](neural-guided-phase-full-panel.md) and
[coloured-wire](coloured-fine-wire-benchmark.md) reports; those outcomes strengthen
the case for testing the missing scene information.

## What context should do

A sky region and a fence beside a train should have different structure priors
and regularization. A spatial feature map can distinguish their locations within
one photograph; a pooled scene vector cannot express that distinction alone.
Use those features to condition smoothness, nuisance/background interpretation,
compatible measurement neighborhoods and refinement allocation. Native RAW
samples should still determine fine orientation, phase, colour, amplitude and
finite support. Texture probability is useful evidence about how to interpret
measurements, not a texture sample to paste into the image.

The comparison must include thin wires/clouds in sky and flat paint/gaps in a
busy region. Otherwise a sky/fence shortcut could look successful while erasing
real sky structure or drawing a mesh across smooth objects. Evaluate final RGB
under correct, shuffled, masked and spatially shuffled scene context. Attention
weights alone do not establish useful reliance.

## Implemented foundation, no quality claim yet

[scene_context.py](../src/demosaic/scene_context.py) now provides:

- A whole-observation CFA preview: area-average the four actual sensor phases,
  average the two greens, apply one explicit scene exposure/WB/matrix, and retain
  aspect ratio. It accepts noisy packed RAW, not a clean target, and never
  enlarges a packed plane. Native dimensions and encoder padding are separate.
- Feature queries at each native tile's real coordinates. Padded scene features
  are sampled in their padded coordinate system, without squeezing rectangular
  padding into the photograph. Multiple tile queries reuse one encoded map.

Eight numerical tests check all four CFA layouts, withheld-input
invariance of an A-only preview, scene calibration, rectangular padding, tile
coordinates, batch-independent queries, feature gradients and FP32 native-coordinate
arithmetic for FP16/BF16 feature maps. These are
plumbing/geometry tests, not restoration scores. No encoder or scene adapter is
connected to V120 yet, no scene-context weights were trained, and no new DINO
forward was made by this work.

For a held-out A→B diagnostic, the **entire scene preview** must be A-only,
including imputation/exposure/noise estimates; using full-RAW scene features
would leak B. Ordinary supervised whole-scene conditioning may use the full
noisy observation, but its scores must not be described as independent held-out
confidence. The full-input and A-only paths need explicit separate provenance.

## Source feasibility and the missing data contract

The existing cleaned90781-photo training manifest preserves full binned-cache
paths, source identities/hashes and native crop boxes. A new manifest/header
inventory checks32 evenly spaced eligible caches, with no original-photo access,
model forward or sensor draws. They are full **binned source fields**, not
necessarily uncropped camera photographs. Cache arrays are linear-sRGB uint16.

|Minimum cached short axis|Training sources|
|---|---:|
|512|90781|
|768|24746|
|1024|1759|
|1536|47|
|2048|3|

These counts are before the current additional2× augmentation reduction. Keeping
that reduction gives only1759 sources with a512-native short axis and47 with768.
It would be misleading to call all90781 sources ready for1024-native scene
training. The existing sampler also crops before camera/noise augmentation and
may apply independent crop homographies. It does not already provide a shared
full-scene noisy observation plus an exactly corresponding native tile.

The first data implementation should draw one camera/exposure/CFA/noise
realization for a complete cached scene, then extract native tiles from that
same observation, with even phase-preserving origins and explicit transforms.
Apply D4 augmentation to the complete scene; initially disable independent tile
homographies/resizing in **every matched arm**. Reuse the exact observation and
crop schedule across arms and record fingerprints. Clean full scenes are targets
for supervision only, never scene-encoder inputs.

Two cohort choices must be explicit: retain the extra2× reduction on the smaller
eligible subset, or test native bin4 scenes from the24746-source >=768 subset.
The latter changes data relative to mature V120, so it needs a matched local-only
control on those same scenes. Do not credit that data change to scene context.
The header inventory is feasibility evidence; it does not admit a new training
cohort or replace the existing protected-family/content-hash exclusions.

## Prospective matched test

Compare no added scene branch, a pooled scene descriptor and aligned spatial
scene features, retaining V120's local encoder/trunk. Use the same frozen DINO
weights, parent checkpoint, observations, crop boxes, training horizon and loss.
A preview long side around1024 is an initial cap, not a measured optimum; smaller
source planes stay smaller. Encode once per noisy scene and share the spatial
features across its crops/tiles. Start with a zero-output adapter so initialization
preserves the base, then verify gradients reach it and final RGB actually depends
on correct context. A local-only adapter is a useful capacity control.

This quality experiment precedes replacing repeated local DINO calls with a
student. Removing local capacity at the same time would confound the missing-
context question. There is no speedup claim from the new utilities.

Retain native noisy/restored/exact-GT triplets and per-source adverse results:
quiet coarse luma/chroma mottle, fine weak/strong response, increment and colour
errors, finite support, tile seams, crop-grid/batch/overlap sensitivity. Both GFX
families remain required: DSCF3879/3880 sky/building/foliage/coarse fence and
DSCF3842/3835 both fine cab ROIs/profiles/JPEGs. ISO100/AHD/JPEG references are
independent qualitative references, not exact GT or pixelwise scoring targets.
Protected captures and siblings remain outside training; originals read-only.

[Exact source/header/test receipts](results/whole-scene-context-foundation-v1/publication.json).

The separate [A-only fine-innovation control](parent-innovation-validation.md)
was already admitted before the user's context steering. Both48-case producers
have closed with zero new neural calls; its quality review stays separate from
the whole-scene architecture test. It is not a substitute for scene semantics.
