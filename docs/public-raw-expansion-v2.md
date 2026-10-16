# Broader public RAW quarantine

The native clean corpus has only 31 original scenes, or 37 with the six-source
public extension. This larger selection investigates more camera-native scene
diversity before another matched quality trial. It is **quarantine**, not an
approved training corpus, and establishes no model quality gain.
[Frozen selection and producer checks](results/public-raw-expansion-v2-startup.json).

The metadata survey inspects 291 catalog entries across 185 camera models and
selects 138 models with explicit per-entry CC0 links and ISO 50–200. It prefers
full-area/high-bit-depth variants at catalog resolution ≥20 MP, investigates up
to two entries per model and selects one low-ISO entry. It excludes previous
pilot file IDs, catalog monochrome/pixel-shift/reduced modes, non-GFX Fujifilm
CFAs and the declared unseen camera models. Nine makes are represented:
Canon, Fujifilm, Hasselblad, Leica, Nikon, Panasonic, Pentax, Ricoh and Sony.
These are camera-model counts, **not verified distinct-scene counts**.

The [publisher](https://raw.pixls.us/) asks for low-ISO scenery and uses explicit
per-entry license links. The selection requires those CC0 links; it does not
infer a license from the site alone. It retains the frozen catalog, original
metadata URLs and payload hashes. Eighteen oversized metadata responses are
recorded and excluded. Spaces in metadata URLs are encoded for retrieval while
retaining the exact catalog URL as provenance.

The frozen survey is
`/mnt/external/demosaic/references/raw-pixls-expansion-v2-scout/survey.json`, SHA256
`c3f4e85966f7164fb77e530c8e5563c2e5742866ebde001144a7077cae46d9fd`.
Acquisition uses the existing tested downloader with two workers, published
SHA256/HTTP byte checks, verified reuse, an output lock and a 512 GiB reserve.
Its complete manifest appears only after every download verifies. The separate
Commons downloader continues under its existing lock.

```bash
source scripts/env.sh
uv run --no-sync python scripts/fetch_public_raw.py \
  --survey /mnt/external/demosaic/references/raw-pixls-expansion-v2-scout/survey.json \
  --catalog /mnt/external/demosaic/references/raw-pixls/catalog.json \
  --output /mnt/external/demosaic/references/raw-pixls-expansion-v2 --workers 2
```

The reusable producer verifies actual source bytes, ordinary Bayer geometry,
actual ISO and size, existing/protected source hashes, unseen camera aliases and
the standing GFX identifiers/date family. It applies the existing phase-aligned
4×/8× binning, with no demosaicer, WB/matrix, tone curve or 8-bit intermediate in
the camera-linear uint16 targets. Source noise is reduced, not eliminated:
these are **low-noise estimates, not exact noiseless GT**.

```bash
source scripts/env.sh
uv run --no-sync python scripts/prepare_public_raw_quarantine.py \
  --acquisition /mnt/external/demosaic/references/raw-pixls-expansion-v2/manifest.json \
  --output /mnt/external/demosaic/raw-pixls-expansion-quarantine-v2
```

Per-capture atomic outcomes let interruption/restart reuse completed targets.
Recipe/source changes or changed cached bytes are rejected. Actual decode
failures and unsupported captures remain explicit rejections. The manifest
retains source/cache hashes, metadata, near-white fractions and inspection-only
renderings. The source clipping criterion remains ≤0.1% of bin4 pixels with
any channel ≥65500; passing it is insufficient for admission.

A genuine GFX50R source reproduces the old producer's bin4, bin8 and screen
cache bytes exactly. Resume reuses both target files without changing mtimes.
All 342 tests pass (26.95 s), including unseen-camera aliases and standing GFX
siblings with differing file numbers. No new review receipt is pinned and no
existing training manifest changes. Remaining steps are actual content/quality
inspection, protected/Commons/native/intra-candidate scene-overlap screening,
explicit admission and a matched full-resolution training/quality trial.
