# Whole-scene context: implementation and next quality test

The user's sky-versus-fence example identifies a missing input. The
[production/context review](weak-detail-global-context-production-review-2026-11-16.md)
proposes the right next architecture experiment: preserve local RAW reconstruction
and the existing local DINO encoder, then add one spatial scene encoding shared
by native tiles. The review's historical evidence cutoff remains unchanged.

Recommended-model inference still sends DINO only the current tile: `inference.py` passes no
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

## Integrated model/data path and completed2k probes

The complete noisy-scene/native-crop path and a trainable scene adapter are now
implemented. Fifty-five focused tests now cover observation, geometry,
inference, canonical-crop context composition and checked frozen-feature reuse.
Actual V120 native256/B4 checks
complete two discarded optimizer updates for each of no-context/pooled/spatial
conditioning. Initialization matches the base exactly on those fixtures;
gradients reach the new adapter and the shared encoder stays frozen. Three
matched2000-update probes have completed in the
[full-corpus/context compute allocation](full-corpus-scaling.md). Their actual
training observation logs match byte for byte. The [matched native review](whole-scene-context-native-review.md)
finds small mixed spatial-context changes on its first two sources and no
convincing new fence/sky-cord recovery. All16 native boards were viewed. The
[64-source/intervention study](whole-scene-context-development64.md) has completed
analysis and eight further native boards: small quiet-coarse gains coexist with
detail/color costs. [Full primary collection is running on CPU](whole-scene-context-primary-admission.md).
V120 stays the general recommendation.
[Exact model/data/preflight receipts](results/whole-scene-context-training-setup-v1/publication.json).
[Independent source/checkpoint audit](results/whole-scene-context-training-setup-v1/independent-review.json).

The corrected frozen trainer uses the canonical sensor-valid objective including
auxiliary mosaic supervision, and retains raw/EMA weights, Adam, Python/CPU/CUDA
RNG and scene draw index. Its three actual two-update preflights pass initial
output parity, gradient/frozen-backbone checks and optimizer/checkpoint reload.
The first admission's preflight omitted the auxiliary term; its production
handoff failed at directory creation before any context update. Both historical
sources/receipts remain intact. Production starts afresh from V120, not the
discarded checks. Training and the first native review are now complete;
the completed development/intervention and running full427/camera reviews are separate.

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
plumbing/geometry tests, not restoration scores. The original foundation made
no encoder calls. The later integrated qualification makes explicit scene/local
encoder calls, counted separately in its new receipts; those discarded updates
do not establish a quality gain.

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

The new [scene observation](../src/demosaic/scene_data.py) and
[photo sampler](../src/demosaic/scene_training_data.py) create one camera/exposure/
CFA/noise realization for a complete cached scene, then extract native tiles
from that same observation. Origins preserve Bayer phase; global D4 transforms,
camera/noise seeds, crop boxes and actual input/target fingerprints are retained.
Independent tile homographies/resizing are disabled in every matched context
arm. Clean scenes are supervision targets, never encoder inputs.

The context probe chooses native bin4 scenes: short axis>=768, at most4MP.
After the size cap,24,660 sources train the adapter/trunk and64 are reserved for
development. Every selected source remains in the later cleaned90,778-photo
cohort; the three later exclusions were already below768 and ineligible.
This changes targets relative to mature V120's extra2× reduction, so the local-
only context control uses exactly the same bin4 scenes. The separate100k scaling
run retains bin4→geometry→area2 and its larger90,778-source pool. Gains from one
data choice must not be credited to the other architecture experiment.

## Prospective matched test

The implemented [scene restorer](../src/demosaic/scene_restoration.py) compares
no added scene branch, a pooled descriptor and aligned spatial scene features,
retaining V120's local encoder/trunk. All arms use the same frozen DINO
weights, parent checkpoint, observations, crop boxes, training horizon and loss.
A preview long side around1024 is an initial cap, not a measured optimum; smaller
source planes stay smaller. Encode once per noisy scene and share the spatial
features across its crops/tiles. The new adapter projects four frozen feature
levels and adds a zero-initialized offset to the trunk's eighth-resolution state.
Tests verify gradient flow and spatially shuffled feature sensitivity. Final RGB
dependence on correct versus shuffled/masked context is being evaluated in the
fixed64-source study. A local-only adapter remains a useful future capacity control.

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
