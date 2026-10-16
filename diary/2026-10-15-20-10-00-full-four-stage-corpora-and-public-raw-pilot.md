# Complete 4× corpora, matched continuation and public RAW pilot

Recorded 2026-10-15 20:10 PDT / 2026-10-16 03:10 UTC.
Previous goal turn was progress (eb88db1): new-source rebinning and the matched
expanded-corpus pilot. The original PROMPT goal remains active and unproven.

V32/V35 both stopped at step2000 with their original optimizer/EMA/RNG and
planned3000 schedules. All51 logged paired/native hashes match across82 logged
observations per arm. V35 improves known primary PSNR over V32 by.04403dB,
95% scene interval[+.03623,+.05304], but loses.06561dB unseen (interval crosses
zero). Its own unseen primary falls.10983dB versus first1k. Known/unseen V32
primary54.25657/53.76436, auxiliary RGB39.98450/38.47228, SSIM.930838/.919339.
V35:54.30060/53.69875,40.03731/38.44141,.931114/.919246. Channel-calibrated
RawNIND still leads all three unseen means. No broad superiority established.

The completed full427 comparison gives V32 first1k/2k photo PSNR33.95672/
34.02439 and SSIM.950119/.950653; V35 gives33.84007/33.90384,.949812/.950506.
Thus both improve on the full panel while their16-photo screens decline.
V32 gains.06767dB[+.04810,+.08519]; V35 gains.06377[+.03578,+.08908]. V35-2k
trails V32-2k by.12055dB[.09661,.14739] in this one-seed pilot. Do not generalize
this to data quantity being harmful: changing corpus size also changes all
Commons sample assignments. Source bootstrap does not cover training-seed noise.
All443 photo/procedural sources, seven conditions/four CFAs and9 methods produce
111,636 rows. V32-2k becomes the stronger full-photographic reference.

Checkpoint SHAs: V32-2k
`d36c5c1a5af1c996d84641db568c6e768d10a759b4048acf5ef6ebc5f6f37ff8`, V35-2k
`5da06ebcac5986de11de941e8a1526ff17bae3e4a1357cecdd16d999b3d2256d`.
Published48 native triplet PNGs across development/full/context reviews, with
two exact synthetic GT examples per new model, fixed ROI/noise/render settings
and matching noisy/reference bytes. Real AHD/ISO100 references remain labeled
accurately. README examples use V32-2k full427/full102MP output. Fine texture,
foliage and mesh remain soft/irregular; a colored point persists.

GFX report tool now optionally includes both RawNIND calibrations, sharing one
immutable upstream network but using distinct gain adapters/buffers. Defaults
preserve historical global CFA-LS. Actual full102MP V32/V35/Raw-global/Raw-channel
restoration took40.24/40.23/20.68/20.17s with eight-worker preparation active.
All8 RGB16/ICC TIFFs passed full SHA/size, shape/dtype/sample tags and sampled
code-count checks. This is not an idle speed comparison;10s remains unmet.

The existing bias diagnostic needed explicit shot/read conditioning for VST
models; fixed that and added both RawNIND calibrations plus immutable-result
guards/provenance. On18 preselected512px center tiles, input-only global/channel
gains lower V35 mean primary50.19500→50.15958/50.06492, with channel gains also
lowering RGB36.35851→35.94631. Median equal-channel DC/MSE fraction is2.81%,
maximum47.94%. Gains can be biased by correlation with noisy inputs. No gain
correction is adopted. This center diagnostic is not the full development panel.

A controlled48-source preprocessing sweep, two shuffled repeats2/4/8 workers,
measures4.19/7.56/12.20images/s, process RSS peaks.93/1.23/1.83GiB. All per-source
cache hashes match across all6 cases. This is preprocessing, not training speed.
The first handoff controller safely returned before stopping the original
producer due to an asynchronous SIGSTOP-state check. Corrected its handshake.
The owned two-worker producer then resumed at eight workers, reusing26,314
caches; the temporary ledger and recipe were archived. Original files and frozen
source selection remain unchanged. No unrelated process was stopped.

At02:53UTC both complete4× manifests froze, zero failures:
base40170train/2303val/2255test, SHA
`22d07361d1b67de077560f6b8571388db699ead2d164201c71fe71ec5755f4c3`;
expanded41978train/same held-out membership, SHA
`475052a7a63eefa7db785023a2b5fe9d4a69e99062dee9e5258c95364cf2bcfc`.
All1,808 new caches completed separately; the extension reuses44,728 old4×
paths without copying pixels. All active identities/splits/credits and4× cache
headers pass the audit. Original freeze waiter resumed and both waiters exited
normally. Remaining18,414 sources plus cached-prefix validation took26m06s.

V34 started02:53:56 and completed first1000 updates03:05:13; V36 is now training
its first1000. Workflow PID280861, `.cache/v34-v36-workflow.log`. Source module
bytes and initializer match the old8× controls. All12 sampled paired draws
through V34 step625 match V32. New data-inclusive source bundle hash:
`15af15b4c3e817599e54d1e3995dbd95f9f14213dace0e3a7735985cef8300ea`;
native4× manifest is the intentional bundle difference. After both first1k
reviews, queued full2×2 evaluation PID443420 will compare all427 photos and
full GFX outputs, including both RawNIND calibrations. No partial producer was
used. Source updates stay out of these controlled trainers.

Added tested `scripts/fetch_public_raw.py`: nine individually CC0 catalog entries
acquired into quarantine,909,367,652 bytes, every publisher SHA256 and HTTP byte
count verified. Reuses the existing checked downloader, two workers,512GiB
reserve, archived catalog/EXIF/source/recipe. Completed files are reused. All9
decode as ordinary Bayer at ISO50–100;18 phase-aligned4×/8× uint16 caches and
their hashes/metadata are retained. These are low-noise estimates, not exact GT.
The resized dataset overview was inspected: eight landscapes/architecture and
one chart, which is omitted from the proposed photographic subset.

Exact-source checks cover211 existing RawNIND/standing captures. No matches.
Cross-render near-duplicate screening of46,738 Commons records plus53 old native
references flags none at dHash≤24/correlation≥.97/aspect3%. Arbitrary crops/views
can evade it; protected-final was checked by source identity only, no new model
or final scoring. Public sources stay `split:quarantine`, outside all active
training and transform fitting. Further admission work remains. Public RAW and
pixel/cache/scene-screen receipts are published with the CC0 inspection overview.

Validation:279 tests passed45.38s; Ruff passed. Seven new acquisition tests cover
license/metadata/catalog identity, standing identifiers, cache reuse and owned
output; one comparator test verifies distinct gain state and shared weights.
Documentation links,48 new native PNG hashes/dimensions and11 authoritative
input-report hashes checked. Full RGB16 and complete4× corpus receipts verified.
Original private photo trees remain read-only. The Commons downloader continues
independently. SOTA/decisive real qualitative superiority, final-architecture
DINO ablation, protected-final evidence and10s/100MP remain unproven.
