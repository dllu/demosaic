# Private GFX100S source preparation

Thirty-one user-authorized local RAWs now have verified private source copies
and62 phase-binned4×/8× camera-linear uint16 caches. **Twenty-two pass the fixed
source-clipping limit; nine fail and remain excluded.** Preparation records stay
in quarantine. A separate pinned admission now permits the reviewed 22 in
private, opt-in 4×/8× extensions containing 150 captures and 120 family labels.
Active quality recipes still use 128 captures/106 groups; no trained data benefit
has been established.
[Producer, source-audit bindings, counts and exact pixel checks](results/personal-native-quarantine-preparation-v1.json).
[Completed loader integration and unchanged-legacy checks](results/personal-native-extension-v1.json).

The source inventory found5,015 local GFX100S RAWs. Among139 captures with editing
sidecars,88 inspection JPEGs report ISO≤200;50 also record f/4 or smaller.
Source-only resized JPEG inspection chose31 architecture, nature, animal and
vehicle frames, avoiding staged product shots, close portraits and near-identical
redundant frames. Actual RAW ISO, camera, capture timestamp and import SHA1 are
verified before preparation. The local source files are read-only; no archive
hard drives were read. About3.25GB of original RAW bytes are cached privately.

The producer uses the existing phase-centroid-aligned Bayer binning, with no
demosaicer, WB/matrix, tone curve, gamma or8-bit stage in target caches. These
are low-noise estimates, **not exact noiseless GT**. The separate inspection
screens use metadata WB/matrix and sRGB. All source pixels, travel/capture
metadata and overviews remain outside Git; permission to use the photos does
not imply a CC0/public-redistribution grant.

Source clipping uses the existing limit: no more than.1% of bin4 pixels may
have any camera channel≥65500. Actual source/caches/screens/previews pass155
file-hash bindings. Independent FP64 scalar filter calculations reproduce72
sampled RGB16 codes across three real sources and both factors with maximum
error0. This verifies source identity and sampled arithmetic, not independent
sensor precision or noiseless targets.

The data-only screen compares45 cached protected references, all94,455 records
in the current Commons manifest,128 existing native captures and the31 new
candidates. Protected references include the standing GFX scene and three other
personal qualitative captures; no protected-final model performance is scored.
No protected or Commons heuristic match is flagged. Cached descriptor algorithm
and coverage are verified; the fingerprint database is opened read-only and its
bytes remain unchanged.

Broad existing-native/intra-source flags reveal related landmark views. Actual
source-only inspection conservatively maps four new views, including a wider
panorama, to one existing training family. The22 passing captures then have15
family labels,14 additional to the existing dataset. This avoids counting
related views as independent scenes. Finite fingerprints and manual inspection
do not establish complete scene independence.

Five focused tests verify copy/reuse identity, unchanged original bytes/mtime,
wrong import-hash refusal, corrupt-cache refusal and allowed source roots.
Ruff/format checks pass. Preparation never modifies an active manifest.

## Separate private admission

The loader accepts only exact rows derived from the SHA-pinned private receipt.
Public code publishes its digest, not the per-photo receipt or source pixels.
Permission and original-source provenance remain attached to private rows;
no public license is assigned. Split, scene, cache or camera edits cannot admit
a quarantine record. Tests also reject stripped provenance markers and
self-signed receipts.

Both extensions preserve all 128 existing rows and the embedded public admission
exactly. Existing manifests and cache modification times stay unchanged. The
new loader reproduces 32 real legacy crops exactly against the frozen previous
loader, covering both bin factors. All 44 newly admitted cache/crop checks pass
shape, uint16, checksum, finite-output and repeatability checks. The original
producer's archived source files still match their pinned checksums after the
loader implementation changes.

A genuine V63/DINO CPU check completes four native-only updates from these
22 private sources at B1/native64/FP32, with finite 99 model / 99 EMA / 97 AdamW
states and all 97 trainable gradients finite at every update. Its original
4,000-update schedule is retained; the short checkpoint is discarded. Tiny real
validation checks execution only. The final CPU suite passes 1,120 tests with
9 skips, including 36 focused native-data tests with 1 skip. No quality claim
comes from this engineering check.

For a separate local extension, source `scripts/env.sh` and run:

```bash
uv run --no-sync python scripts/extend_personal_native.py \
  --base /mnt/external/demosaic/raw-clean-public-extension-v2/bin4/manifest.json \
  --admission .cache/personal-native-admission-v1/admission.json \
  --output .cache/your-private-native-extension/bin4
```

Use the bin8 base for the companion extension. The prepared private manifests
are `.cache/personal-native-extension-v1/bin4/manifest.json` and its `bin8`
counterpart. The nine rejected captures stay excluded. Quarantine manifests
still fail the loader. These additions need a matched trained comparison before
claiming a quality benefit or changing the active recipe.
