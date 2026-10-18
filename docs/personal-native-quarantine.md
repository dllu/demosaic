# Private GFX100S source preparation

Thirty-one user-authorized local RAWs now have verified private source copies
and62 phase-binned4×/8× camera-linear uint16 caches. **Twenty-two pass the fixed
source-clipping limit; nine fail and remain excluded.** All new sources remain
in quarantine, which the current loader rejects. Active training still uses128
native captures/106 groups. No model has trained on this addition.
[Producer, source-audit bindings, counts and exact pixel checks](results/personal-native-quarantine-preparation-v1.json).

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
Ruff/format checks pass. Preparation never modifies an active manifest. Pinned
loader integration, unchanged legacy-loader checks and a matched trained study
are still required before claiming a data benefit or changing the recipe.
