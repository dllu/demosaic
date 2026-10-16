# Camera-linear training targets from low-ISO RAWs

The optional native-target source avoids the rendered JPEG, inverse-gamma and
approximate camera-unprocessing stages used by Commons training. It starts from
the already downloaded public **training** references, retaining each camera's
white balance and color matrix. This is a data experiment, with no demonstrated
quality gain in the original matched source-substitution trial. Newer
[pretrained restoration trials](anchored-stabilized-rgb-v30-review.md) use this
source in a broader mixture; its independent contribution remains unresolved.

The V20/V21 pilot starts from the same frozen V16 step5000 EMA and updates only
the fine RGB correction branch, with seed 44, LR 3e-5 and a planned 5000-step
schedule. Both stop for review at 1000. V20 substitutes native targets for half
the non-paired batches; V21 retains the existing 50/50 paired/synthetic recipe.
Both enable per-step data RNG and observation tracing. Configs are
`configs/dino-native-target-v20.yaml` and `configs/dino-native-control-v21.yaml`.
No inference default changes while these experiments run.

Both stopped at step1000. The [matched review with native crops](native-target-review.md)
finds no convincing quality gain, so neither candidate is promoted.

The first cache contains 53 captures from 31 scenes: 46 Sony ILCE-7C, four Canon
EOS 6D and three Nikon Z6 captures, at ISO 50/100. It occupies 118,193,524 bytes.
The two Nikon D40 references are rejected because their 8× binned images are
smaller than the 256-pixel training patch. Originals remain read-only.
[Source, cache, recipe and separation receipts](results/native-raw-clean-train32.json).

```bash
source scripts/env.sh
uv run --no-sync python scripts/prepare_raw_clean.py \
  --manifest /mnt/external/demosaic/references/rawnind-train32/manifest-train.json \
  --output /mnt/external/demosaic/raw-clean-train32-bin8-v1
```

Preparation black/white-normalizes the Bayer samples using RAW metadata. Each
of the four CFA phase grids is shifted by a quarter phase-grid pixel before
4×4 averaging, making all channel centroids coincide at the centers of an 8×8
sensor block. The green phases are averaged together. A one-cell border removes
the interpolation boundary. Separate unaligned channel boxes would have
different centroids and generate color fringes on edges. This construction has
matching second moments across phases, at the cost of a slightly wider filter
than an ideal dense-RGB box average.

Targets are quantized once to uint16 after clipping to [0,1]. No demosaicer,
white balance, color matrix, tone curve or 8-bit intermediate enters the cache.
These are **low-noise estimates, not exact noiseless RGB GT**: source noise,
clipped highlights and optical limitations remain. Per-image caches contain
9,846–47,494 distinct uint16 codes; this does not establish that many bits of
independent sensor information. Source hashes, camera metadata, attribution and
cache hashes are retained. Preparation is locked, resumable and recipe checked.
The publisher's per-scene `permissions.txt` is checksum verified and copied
beside the prepared manifest, preserving individual credits with the cache.

Training samples scenes uniformly, then captures within each scene. Crops use
shrink-only scaling, rotations/flips and existing optical/geometry augmentation.
Fresh exposure, Bayer pattern and Poisson/read/ADC noise are applied directly in
camera units, using the same physical noise prior and losses as existing
synthetic training. Camera metadata travels with the crop.

Set `raw_clean_manifest` to the prepared manifest and `raw_clean_fraction` to a
batch proportion. With `paired_fraction: 0.5` and `raw_clean_fraction: 0.25`, the
expected mix is 50% paired RAW, 25% native-target synthetic and 25% Commons/
procedural synthetic. The paired schedule is preserved. Native fraction zero
preserves the previous pipeline and RNG behavior.

For matched source-substitution trials, enable `data_seed_per_step: true` in
both arms. This isolates noise draws by seed/global step so a substituted batch
cannot shift later shared observations. `trace_observations: true` records
sampled batch hashes. Resume refuses changed native manifests, proportions or
RNG protocol. CPU tests verify identical full/resumed model weights, EMA and
observation hashes in native-only and three-source runs. CPU/CUDA tests verify
RNG isolation. A 16-step CUDA run using the real cache exercised all three
domains with finite losses/gradients. The complete suite passes: 176 tests.

Only the predeclared train32 acquisition references enter this cache. They are
a subset of the previously audited training sources, disjoint from protected
scene IDs and exact capture identities. The earlier Commons perceptual screen
covers one reference per scene, not a complete near-duplicate proof. Development,
final test and the user's GFX qualitative captures remain excluded.

Source: Benoit Brummer and Christophe De Vleeschouwer, *Raw Natural Image Noise
Dataset (2025)*, [dataset](https://doi.org/10.14428/DVN/DEQCIM),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Individual scene credits and additional CC0 grants are in the acquired
`permissions.txt`.

## Augmentation before the final reduction

The4× cache now contains the **same53 captures/31 scenes** as the8× cache,
474,370,336 bytes with the same verified source identities, protected exclusions
and `permissions.txt`. Its minimum side is512px. Set
`raw_clean_augmentation_downsample: 2` with this manifest to crop/scale/rotate
and apply optical PSFs at twice the final target resolution, then average2×2
cells before camera exposure/Bayer/noise simulation. WB and camera matrix remain
attached to each camera-linear sample. Registered paired RAW retains its exact
sensor-phase transforms.

```bash
source scripts/env.sh
uv run --no-sync python scripts/prepare_raw_clean.py \
  --manifest /mnt/external/demosaic/references/rawnind-train32/manifest-train.json \
  --output /mnt/external/demosaic/raw-clean-train32-bin4-v1 \
  --factor 4 --min-size 512
```

The option requires declared4× caches and sufficient native dimensions; resume
rejects a changed augmentation recipe. Defaults retain the original8× path.
Tests cover camera units/metadata, source-cache integrity, noise-free mosaicing,
protected-source rejection and exact mixed-data restart. See
[cache/source receipt](results/native-four-stage-startup.json) and
[the combined Commons/native trial recipe](../configs/dino-anchored-pre-downsample-b16-v34.yaml).
These remain low-noise estimates, **not exact noiseless RGB GT**.

Additional native-RAW source survey (2026-10-15): the [raw.pixls.us catalog](https://raw.pixls.us/)
contains 2016 entries in the fetched snapshot, of which 1870 individually link
to CC0, covering 925 distinct make/model pairs. Legacy entries with other
licenses are separate. Nine inspected candidate metadata files span Nikon Z7/
Z7II, GFX50R/GFX100S, Leica Q2/SL2, Sony a7RIV/a7RV and Panasonic S1R, all
ISO50–100. [Catalog hash, entry license links and metadata receipts](results/public-raw-candidate-survey.json)
are retained. This is a source survey: no RAW pixels have been downloaded,
prepared, scored or added to training. Published catalog labels can describe
compression modes imperfectly; verify actual Bayer geometry and bit depth.
Camera samples may overlap the user's own contributed/public photos or existing
protected scenes. A checksum and scene/near-duplicate audit must precede any
new training manifest. These candidates do not change the matched V24/V25 data.

The subsequent [public RAW pilot](public-raw-pilot.md) has now acquired and
decoded nine checksum-pinned CC0 samples into separate4×/8× quarantine caches.
Eight show landscapes/architecture; one color-chart sample is omitted from the
proposed photographic subset. No source identity or near-duplicate matches were
flagged in the documented checks, with stated scene-screen limitations. This is
not yet training admission and changes none of the53-source native targets used
by V32/V34/V35/V36.
