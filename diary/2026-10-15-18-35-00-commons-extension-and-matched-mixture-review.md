# Commons extension and matched lower-LR review

Recorded 2026-10-15 18:35 PDT / 2026-10-16 01:35 UTC.

The existing downloader continues at 0.5 request starts/s with three workers and
a 512 GiB reserve. At 01:34 UTC the archive contains 80,306 verified originals
(208.4 GiB), versus 77,025 at restart; two additional failures are recorded by
the downloader and pending work remains resumable. No duplicate downloader was
started. About 1.8 TiB remains free on the external SSD.

Added `scripts/expand_commons.py`. Its first frozen selection prepares 2,006
newly downloaded, freely licensed sources at linear 8× resolution and screens
them against all 44,732 existing records. Exact-cache matches, dihedral dHash,
aspect ratio and thumbnail correlation form conservative duplicate clusters.
New clusters touching any existing source are excluded. New validation/test
buckets are reserved rather than extending active evaluation. The result adds
1,808 training sources, reserves 196 and excludes two. All old records and
validation/test memberships remain exactly identical. Descriptor caching avoids
re-reading old pixels in subsequent extension audits; all first-seen cache
checksums were verified. Near-duplicate screening is not complete scene
recognition. A read-only Commons metadata sanity check found no standing GFX
capture identifiers; missing metadata and changed views remain limitations.

Frozen extension manifest:
`/mnt/external/demosaic/commons-extension-20261016-v1/audit/manifest.jsonl`,
SHA256 `38ac5fc61892ee31ddf841ad2b06ebf5ec68b6cb2196b4f7aa97b49775cbfb78`.
The implementation files were archived with pre-start mtimes and hashes while
the process ran. Selection and complete audit receipts are published under
`docs/results/commons-extension-20261016-v1.json`. Active recipes do not change.

V32/V33 both completed their first 1,000 updates from the same V30 EMA, fresh
optimizer/EMA, seed 46, batch 16, LR 3e-5 and planned 3,000-step schedule. The
only recipe difference is paired fraction 25% versus 50% (native remains 25%).
All 27 logged same-domain intersections match, 41 logged observations per arm.
Their original frozen 8× data excludes GFX/siblings and protected-final sources.

The full 427-photo synthetic suite gives V30/V32/V33 PSNR 33.78382/33.95672/
33.83358 and SSIM .947305/.950119/.949587. V32 gains .17289 dB versus V30,
95% source-bootstrap interval [+.13318,+.21321]; V33's +.04975 interval includes
zero. V33 improves our real rendered means, but loses .12672 dB unseen measured
CFA versus V30. Channel-calibrated RawNIND still leads all three unseen real
means; both calibrations are shown explicitly in the report.

Full 102 MP V30/V32/V33/RawNIND restorations took 36.14/35.42/35.77/18.42 s
in successive shared-machine runs. All eight linear/sRGB TIFFs passed complete
hash/size and RGB16/ICC checks. Full-frame native foliage/fence crops still show
soft foliage, irregular mesh and a colored point. Published 32 native PNGs,
including at least two noisy/restored/exact synthetic GT triplets per new model.
No crop resizing; source/ROI/noise/render metadata and identical noisy/reference
panel bytes checked. The README uses V32 synthetic and V33 full GFX examples;
ISO100/AHD references remain accurately distinguished from exact synthetic GT.

V33 resumes its original schedule only to step 2,000 for another real/synthetic/
GFX review. This workflow is detached under `.cache/continue-review-v33-2k.pid`;
training has reached step 2,000 and review follows. V32 remains the stronger
synthetic reference and V34 augmentation control. Complete Commons 4× preparation
continues independently (over 15,000 sources prepared, zero failures at last
check); the waiting freeze gate and V34 future-manifest path prevent partial
training. Native 4× preparation is already complete. No new corpus or geometry
recipe has silently entered the ongoing matched trials.

Validation: full suite **260 passed in 32.71s**; Ruff passed on the new script
and tests. Four extension tests cover reserved groups, old-split anchoring through
duplicate bridges, rotated matches, changed cached pixels and concurrent output
ownership. Documentation link/anchor checks and all 32 published crop hashes/
dimensions passed. The goal remains active: substantial real qualitative
superiority, protected-final evidence, final-architecture DINO ablation and the
10-second target are not established.
