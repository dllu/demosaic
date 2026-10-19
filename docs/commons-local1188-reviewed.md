# Reviewed local Commons extension: 85,757 future training sources

A separate frozen corpus adds **890 training sources** to the existing84,867,
with matching4×/8× active source membership. All2,303 old validation and2,255
test sources remain unchanged. The running V84/V85 comparison retains its
original84,867 Commons sources; this extension needs its own declared recipe.
No trained quality benefit is established here.
[Source, review, cache and loader receipts](results/commons-local1188-reviewed-v1.json).

| New-source disposition | Count |
| --- | ---: |
| Prepared at both scales | 1,188 |
| Protected-screen flags, kept out | 9 |
| Reserved validation/test hash buckets | 104 |
| Withheld for title/series risk | 184 |
| Withheld without shared title-retrieval features | 1 |
| Added to future training | 890 |

The [recovered preparation and duplicate audit](commons-local-memory-recovery.md)
checked all1,188 source/cache identities and both scales, with maximum one-code
cross-scale difference. Pixel screening found no new duplicate exclusions among
the1,179 protected-screen-clear arrivals. That does not settle source-family
overlap: actual source-only title-neighbor review reveals shared sites, named
outings and capture series with different framing or subjects.

All **1,179 resized content thumbnails on12 sheets** were actually viewed.
They contain architecture/interiors, urban/transport scenes, foliage and natural
textures, coasts/water, mountains/sky/snow, wildlife/macros, people/sports and
night lighting. Museum/specimen/product photographs, a map and a bird montage
are also present. No obvious broken thumbnail render appears. This content
screen does not establish native sharpness, noise quality or independent scenes.
No image pixels or attribution records are rewritten.

The title screen retrieves neighbors against **9,660 nontraining anchors**:
every existing validation/test/reserved row plus104 newly reserved arrivals.
It uses accent-folded letter-token character4grams and smooth-IDF cosine, with
numeric tokens dropped. Every new training candidate scoring≥.55 is withheld.
One Greek-titled source has no shared retrieval features and is also withheld;
that does not imply a defective title or image. The threshold is a conservative
data-review choice, without any new model-quality scores.

Actual review covers48 high-ranking existing-source pairs and nine additional
new-reserved pairs. Examples include the Eiffel Tower, Courtenay Gate, church
exterior/interior/detail views, named walks and same-event boats. The retrieval
also produces false positives from vehicle names, species and broad locations.
Those flags remain withheld in this provisional extension rather than being
automatically released. Missing metadata, aliases and other views can evade
these finite checks; complete scene independence is not proved.

The freezer preserves all **89,425 old4× rows and94,455 old8× rows**, including
their literal file bytes and held-out assignments. New4× contains the890 added
training members. New8× additionally records104 reserved and185 excluded
members. Both active training sets contain85,757 sources, with unchanged
evaluation membership. The nine protected-screen flags remain outside both.
All1780 new training cache SHA-256/header checks pass, covering9,478,453,220
bytes. Parent/source arrays are reused directly, without copying or resampling.

An independent actual-loader audit forces every one of the890 new sources
through native256 cropping and the real4×→geometry/PSF→area2 path, with procedural
and flat draws disabled to ensure source coverage. All outputs are finite,
contiguous FP32 RGB;16 repeated crops match exactly. All44 package files match
the actual running training source. This is a loader check, not a global
training-distribution or throughput benchmark, and includes no model inference.

One crop has157 values up to`1.000000238418579`, two FP32 steps above1, so the
first strict[0,1] assertion is preserved as failed. The completed diagnostic
still visits all890 sources. Eight direct NumPy FP64 convolution calculations
confirm accumulation rounding: the input is bounded[0,1] and the positive13×13
kernel's FP64 sum is`.9999999679423315`, so exact arithmetic cannot exceed1.
The largest excursion is **.015625 of one input uint16 code**. The source cache
remains valid uint16; no clamp, source pixel, loader or model implementation changes.
The final review records this small excursion explicitly rather than claiming
strict[0,1] output.

Twelve focused admission tests reject held-out promotion, overlapping/omitted/
duplicate decisions, unreviewed content, changed proof bytes and raw holdout
labels that were not reserved. Together with the11 current data-trial guards,
23 tests pass; Ruff passes. The earlier title-report fixture's empty-list sum
error is preserved; a fresh corrected v3 report completes. Neither cache
preparation nor the current trainer was restarted.

Frozen future manifests:

- 4×: `/mnt/external/demosaic/commons-local1188-reviewed-20261019-v1/manifest4.jsonl`,
  SHA256 `f0728084120cc0c207af73d3f19784d2db64ee588ff4244fadae837171602c74`.
- 8×: `/mnt/external/demosaic/commons-local1188-reviewed-20261019-v1/manifest8.jsonl`,
  SHA256 `0b65f6519917403da7a62cdc57dec166d05df05c6a7a7647717a80c07616e0cc`.

The full review and source overviews remain under
`/mnt/external/demosaic/commons-local1188-content-review-20261019-v1/`.
The freeze, complete cache hash inventory and independent loader/range audit
remain alongside the manifests. The original Commons photos, old manifests,
cached standing GFX scene/siblings and all current experiment inputs are unchanged.
