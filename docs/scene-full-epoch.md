# Full-epoch training with matched whole-image context

This continuation tests whether aligned scene features can improve a native
RAW query's weak-detail recovery and keep smooth regions quiet. The
[earlier matched run](expanded-scene-spatial12k.md) used 24,000 photos per arm.
Its context benefit was small at ISO400, response fell at ISO6400, and the
fine GFX crossings remained incomplete. The
[localized-contrast comparison](scene-local-contrast-2400.md#completed-64-photo-comparison)
found almost identical ISO6400 fine-increment error with or without aligned
scene features, with higher variation in the spatial model's exact flat cores.

## Training design

Both arms start from Corpus 100k EMA
`87b96f3c487b9edaf1c477742b6c38f2a82cc6b20a94716d51cc8cf46a17a760`.
The local-only arm retains the native V120-style trunk. The spatial arm adds
the existing zero-output adapter, with spatial features registered to the
native query and injected at eighth resolution. Its additional preview is
built from the same noisy full Bayer observation as the four native queries.
The preview uses an aspect-preserving 1,024-pixel long side. Both arms freeze
the same DINO backbone and train the same sensor-valid reconstruction loss.

| Quantity | Declared per arm |
| --- | ---: |
| Updates | 50,000 |
| Scene observations | 100,000 |
| Distinct eligible training photos | 90,692 |
| Updates through the first complete shuffled pass | 45,346 |
| Further visits from the second shuffled pass | 9,308 |
| Native 256×256 bin4 query slots | 400,000 |

The complete pass visits 66,692 more source IDs than the earlier matched
12k continuation. Each visit draws native crop positions, global D4
augmentation, a camera recipe and corruption from the global index. The
current 100k full-model parent had previously visited these photos under
its bin4 → geometry → area2 ordinary-photo recipe. The new study tests
wider coverage at native bin4 with whole-image context. These two changes
describe the new study as a whole. The two new arms use identical data.
Canonical validation/test IDs, the 64 reserved scene development fields and
both protected GFX families remain outside this continuation.

Each scene has a 50% chance of a localized modification before camera and
Bayer simulation. One quarter of those modifications supplies an exact
constant-color center, with a smooth transition into the photograph. The
other three quarters retain a weak version of the original local texture.
Ordinary scenes make up the other half. A pad-free native center is tested
inside the 256×256 query. Other crops can overlap and share the same Bayer
observation. This exposes the model to plausible weak structure and exact
smooth targets within real surroundings.

Each arm uses BF16 training, 100 warmup updates, peak trunk/adapter
rates 3e-6/1e-4, and 0.999 EMA on one 50,000-update cosine schedule.
The workers alternate matched milestones. Each phase restores the raw
weights, EMA, Adam state, RNG state and global scene index from its previous
checkpoint. Every completed phase retains source IDs, crop boxes, camera and
noise seeds, and crop fingerprints. The controller compares the full input
trace between arms. Phase receipts record training, data read/CPU auditing
and checkpoint write times. Data time includes memory mapping, cache
verification, augmentation, sensor simulation and CPU fingerprinting.

## Quality comparisons

The scheduled monitor replays the fixed held-out scene panel at matched
2k, 5k, 12k and 25k states on eight photos, and at 50k on all 64. It compares
V120, Corpus 100k and both new EMAs. The aligned arm also receives a masked
guide, a blurred distant view and a mirrored distant view with the query
and its preview halo preserved exactly. The primary texture measures are
phase-aligned weak response and increment error. The exact flat regions
measure false structure and color bias under coupled and independent draws.
[Panel construction and measurements](scene-local-contrast-2400.md#held-out-test-for-true-detail-and-flat-regions).

The completed endpoints require the fixed 427-photo and known/unseen
camera panels, 100% exact-target triplets, and both standing GFX100S
comparisons. Collection jobs wait for the matched 50k endpoints. The
fixed-panel worker first qualifies both endpoints on three archived cases.
The main scene covers fence, foliage, sky and building.
The fine green cab review covers left and right crops under both noise
profiles. Its ISO100 and camera JPEGs are independent qualitative references.
Training, numerical collection and native viewing are recorded separately.
Full-frame GFX preview resolution relative to a native query remains a
known distribution difference.
[Endpoint collection queue](results/scene-full-epoch-v1/endpoint-review-queue.json).
The corrected endpoint renderer writes output inside the frozen worker’s
directory. The 2,000-update review verified that path. The
corrected endpoint worker is waiting for the 50k checkpoints.
[Native collector recovery receipt](results/scene-full-epoch-v1/endpoint-native-recovery.json).

The previous waiters were bound to the first training controller and exited
after its RAM-floor stop. Seven receipt-driven workers now wait for verified
matched checkpoints across controller restarts. These include a new matched
5k monitor and both standing GFX families at 5k, the three already planned
12k, 25k and 50k monitors, and the original two endpoint collectors.
[Replacement queue and older failure logs](results/scene-full-epoch-v1/resilient-review-queue.json).

## Execution status

Both CUDA qualifications passed. Each initial zero-output model reproduced the
parent prediction exactly and both arms saw identical Bayer inputs and clean
targets. Both production arms completed eight updates using the same 16 photos
and 64 crops, including two exact-flat and five weak-texture scenes. The local
arm then restored its update-eight checkpoint and continued from scene index 16.
The first recovery started after both arms
completed 2,500 updates, with verified matching inputs for 5,000
distinct scenes and 20,000 native queries each. The local worker reached
update 4,500 on its way to the 5,000 milestone before the runtime RAM
reserve stopped it. Its phase had no saved checkpoint. The controller
restarted from the verified 2,500 checkpoint and the first 942 replayed
scene records match the interrupted attempt byte for byte. At that point
numerical and native reviews were complete through 2,000.
[Restart receipt](results/scene-full-epoch-v1/retry-005000.json) ·
[Original failure and retry logs](results/scene-full-epoch-v1/retry-005000-evidence.tar.xz).

A second memory-floor stop came after local update 4,491. The recovery
controller now asks the frozen worker to save state every 500 updates
or sooner at an original milestone. It keeps the original memory
limits and preserves individual segment receipts. Reaching a matched
milestone requires identical concatenated observation traces in both
arms. The frozen 50,000-update learning-rate horizon, source order,
checkpoints, EMA and validation schedule remain in use. A repeated
RAM-floor stop now replays at most one 500-update segment.
The first local segment now has a verified checkpoint at update 3,000.
Its 1,000 scene records match each interrupted attempt byte for byte.
The update-3,500 segment has resumed from that stored optimizer and EMA
state. The most recent matched pair at this recovery was update 2,500.
[Recovery controller](../scripts/resume_scene_full_epoch.py) ·
[First durable segment and original worker identity](results/scene-full-epoch-v1/segmented-recovery.json) ·
[Second failure and durable restart evidence](results/scene-full-epoch-v1/segmented-recovery.tar.xz).

The local arm subsequently verified update 4,500, covering 9,000 distinct
photos and 36,000 native queries across its durable prefix. A third RAM-floor
stop came after update 4,939. The controller kept update 4,500 and queued the
last 500-update segment for automatic retry under the original limits.
Those stops left the matched and reviewed milestones at 2,500 and 2,000.
[Automatic retry and local prefix audit](results/scene-full-epoch-v1/automatic-memory-recovery-005000.json).

Both arms have now reached **5,000 verified matched updates**. Each has
seen the same 10,000 distinct photos, 10,000 distinct noise seeds and
40,000 native queries. The observation traces match byte for byte.
They contain 4,958 ordinary, 3,785 weak and 1,257 exact-flat scenes.
The retained worker loops total 2,349.22 s local and 3,117.55 s spatial,
including 640.54 s and 667.47 s of reader/CPU fingerprinting time.
Checkpoint writes took 4.90 and 5.01 s. These figures cover retained
training segments. The frozen schedule has advanced into the next phase.
[Matched 5,000 update, source, time and checkpoint audit](results/scene-full-epoch-v1/matched-005000-training.json) ·
[Earlier paired segment prefix](results/scene-full-epoch-v1/paired-prefix-004000.json) ·
[Earlier local 5,000 prefix](results/scene-full-epoch-v1/local-005000-prefix.json).
[Launch and state bindings](results/scene-full-epoch-v1/launch-publication.json) ·
[Frozen order, first traces and monitor source](results/scene-full-epoch-v1/launch-evidence.tar.xz).

Both arms' first 2,000 updates cover the same 4,000 distinct sources,
4,000 distinct noise seeds and 16,000 native crops. Their observation
logs match byte for byte. The scenes include 1,981 ordinary, 1,467 weak
and 552 exact-flat examples. Summing the two measured phase loops gives
882.57 s for local-only and 1,152.02 s for spatial. The local reader
and CPU fingerprinting account for 257.88 s. Both runs continue on
their original learning-rate schedules.
[Local prefix audit](results/scene-full-epoch-v1/local-2000-source-audit.json).

An end-to-end monitor qualification used the matched update-eight
checkpoints. It ran all seven policies on 32 test groups, checking
the fixed local input and the preserved near-preview support in 96
native queries. The monitor generated four native boards and the
expected summary. The matched update-2,000 quality collection is
complete on that same eight-photo panel.
[Monitor qualification](results/scene-full-epoch-v1/monitor-preflight.json).

## First matched quality comparison at 2,000 updates

The eight-photo monitor contains 32 paired groups across ISO400 and
ISO6400 and both draw laws. The seven policies process 96 native queries
each. Local EMA SHA256 is
`7f59fe60437e278e550a6abeaf65156c7fb0094d80d2711f9fcbbbd918f71383`.
Spatial EMA SHA256 is
`25867a55eec2423f79d5c05a302184b8871c504de427d9bfee3e1184584d7f64`.
The two distant-view interventions retain the exact query and nearby
preview pixels. Collection used CUDA IEEE FP32 and took 177.9 s
after loading the checkpoints.
[Checkpoint bindings and per-source results](results/scene-full-epoch-v1/matched-002000-pilot.json).

| ISO6400 model or preview | Coupled increment RMS, DN16 | Coupled flat RMS, DN16 | Independent increment RMS, DN16 | Independent flat RMS, DN16 |
| --- | ---: | ---: | ---: | ---: |
| V120 | 84.243 | 4.832 | 103.838 | 4.707 |
| Corpus 100k | 84.218 | 4.208 | 103.983 | 4.127 |
| Local 2k | 83.856 | 4.559 | 104.316 | 4.235 |
| Spatial 2k, matching | 84.097 | 4.438 | 104.431 | 4.260 |
| Spatial 2k, masked | 83.822 | 4.800 | 104.422 | 4.343 |
| Spatial 2k, mirrored distant view | 84.191 | 4.457 | 104.310 | 4.254 |

The correct preview lowers coupled flat RMS by 0.362 DN16
[−0.894, −0.005] relative to its masked control, while raising
increment error by 0.276 DN16 [+0.082, +0.502]. Its independent
increment RMS is 0.115 DN16 higher than local-only with a paired
interval spanning zero [−0.363, +0.485]. The mirrored distant view
is also close. The two EMA continuations show no clear weak-detail
gain on this intermediate panel. The full benchmark and standing
reviews remain scheduled for the final endpoints. Both standing GFX
families have also been reviewed at this intermediate checkpoint.

The triplets show noisy Malvar, spatial 2k with the matching preview,
and exact GT. The two ISO6400 independent draws use shot/read
`0.00128/6.5536e-6`, ADC16 black 0.03, capture exposure 0.33,
display exposure ×3.0303 and contrast ×2. The native 160×160 windows
start at `[48,48]` inside the 256-pixel query.

![Hauroth, noisy, spatial 2k and exact GT](images/scene-full-epoch-v1/pilot-002000/000-iso6400-independent-role0-triplet.png)

The stone's fine grain remains soft. Query `[218,192]`, RGGB.
Palauenc05, CC BY-SA 4.0.
[All methods](images/scene-full-epoch-v1/pilot-002000/000-iso6400-independent-role0-comparison.png) ·
[Exact-flat counterpart](images/scene-full-epoch-v1/pilot-002000/000-iso6400-independent-role2-comparison.png).

![Limburg Cathedral, noisy, spatial 2k and exact GT](images/scene-full-epoch-v1/pilot-002000/001-iso6400-independent-role0-triplet.png)

The arches and columns are retained. The fine architectural features
stay blurred in both the local and spatial outputs. Query `[22,250]`,
BGGR. Full source and license details are in the viewing record.
[All methods](images/scene-full-epoch-v1/pilot-002000/001-iso6400-independent-role0-comparison.png) ·
[Exact-flat counterpart](images/scene-full-epoch-v1/pilot-002000/001-iso6400-independent-role2-comparison.png).

### Standing GFX100S at update 2,000

All eight standing boards were viewed. Both arms keep the DSCF3879
sky smooth and both coarse fence directions visible. Thin building
cables and fine leaf boundaries remain soft. In the separate DSCF3842
fine cab, faint diagonal modulation appears under the transferred
DSCF3879 prior and the fine crossings remain incomplete in both ROIs.

The spatial and local outputs differ by 0.92 DN16 camera-RGB RMS in
the sky, 9.76 DN16 in the coarse fence, and 2.03–4.13 DN16 in the
four cab views. These measure model differences. The ISO100 AHD
and camera JPEGs are independent qualitative references. The
CPU IEEE FP32 review checks identical saved Bayer inputs and noise
conditioning. Local and spatial collection took 252.24 and 295.52 s
respectively for the ten archived observations.

The main native 160×160 crops remain at `[176,176]` in their
512-pixel queries. Shot/read is `0.00128/6.5536e-6` with display
exposure ×4. The cab crops in the 768-pixel query remain at
`[206,229]` and `[426,189]` with display exposure ×16. The
transferred profile uses `0.0014635775921166604/1.0715704128646712e-6`.
[Complete standing receipt](results/scene-full-epoch-v1/matched-002000-standing.json) ·
[Sky](images/scene-full-epoch-v1/standing-002000/main-overcast-sky-main-overcast-sky.png) ·
[Building](images/scene-full-epoch-v1/standing-002000/main-building-detail-main-building-detail.png) ·
[Foliage](images/scene-full-epoch-v1/standing-002000/main-foliage-main-foliage.png) ·
[Coarse fence](images/scene-full-epoch-v1/standing-002000/main-chain-link-fence-main-chain-link-fence.png).

| Cab profile | Native views |
| --- | --- |
| Nominal | [Left](images/scene-full-epoch-v1/standing-002000/mesh-nominal-fine-green-mesh-left.png) · [Right](images/scene-full-epoch-v1/standing-002000/mesh-nominal-fine-green-mesh-right.png) |
| Transferred | [Left](images/scene-full-epoch-v1/standing-002000/mesh-profile3879-fine-green-mesh-left.png) · [Right](images/scene-full-epoch-v1/standing-002000/mesh-profile3879-fine-green-mesh-right.png) |

## Matched quality comparison at 5,000 updates

The same eight-photo monitor ran 32 paired groups with seven inference
policies in 109.97 s of CUDA IEEE FP32 inference. The local checkpoint
SHA256 is `e860f7f7ea2fcdfd18dc3597ec382ea83bc2d00f083c2809735f18765e4ca546`.
The spatial checkpoint SHA256 is
`14cff19b95fc19cb051113efb36a22567b6b2ef85bce218bc6571d85c6d88a23`.
Both use EMA weights. The control metrics for V120 and Corpus 100k
are identical to the 2,000-update review.
[Per-photo metrics, checkpoint bindings and reviewed crops](results/scene-full-epoch-v1/matched-005000-pilot.json) ·
[Paired photo-level intervals](results/scene-full-epoch-v1/matched-005000-pilot-paired.json).

| ISO6400, coupled draws | Fine-increment RMS, DN16 | Fine flat RMS, DN16 | Fine weak response |
| --- | ---: | ---: | ---: |
| V120 | 84.243 | 4.832 | 68.275% |
| Corpus 100k | 84.218 | 4.208 | 68.175% |
| Local 5k | 84.703 | 4.357 | 67.225% |
| Spatial 5k, matching | 84.876 | 4.226 | 67.056% |
| Spatial 5k, masked | 84.564 | 4.643 | 67.385% |
| Spatial 5k, blurred distant view | 84.883 | 4.163 | 67.105% |
| Spatial 5k, mirrored distant view | 84.963 | 4.211 | 66.994% |

On coupled ISO6400 draws the aligned preview reduces flat variation
by **0.417 DN16** versus masking (paired 95% interval −0.958 to −0.037).
It raises increment error by 0.313 DN16 (+0.142 to +0.488) and reduces
signed weak response by 0.330 points (−0.478 to −0.081). Against the
mirrored distant view the matching preview gains 0.061 weak-response
points (+0.001 to +0.142) with flat RMS essentially tied. This comparison
preserves the query and nearby preview halo. Against local-only,
the weak response difference is −0.169 points (−0.374 to +0.119).
Against Corpus 100k the aligned weak response falls by 1.119 points
(−1.704 to −0.249), with similar flat variation. On independent draws,
it gains 0.074 points over mirroring (+0.013 to +0.145) and loses
0.998 points to Corpus 100k (−1.690 to −0.152).
Compared with the matching 2k checkpoint, the coupled increment error
is 0.779 DN16 higher and the independent increment error is 0.358
DN16 lower. Both draw laws have lower weak response at 5k.

The two triplets show noisy Malvar, spatial 5k with matching preview
and exact GT at native 160×160. The first independent ISO6400 weak
roles use shot/read `0.00128/6.5536e-6`, ADC16 black level 0.03,
capture exposure 0.33, display exposure ×3.0303 and contrast ×2.
The ROI is `[48,48,160,160]` in both 256-pixel queries.

![Hauroth, noisy, spatial 5k and exact GT](images/scene-full-epoch-v1/pilot-005000/000-iso6400-independent-role0-triplet.png)

Hauroth, query `[218,192]`, RGGB, Palauenc05, CC BY-SA 4.0. The matching
and mirrored previews show similar stone grain, with the exact patch
visibly crisper. [Full comparison](images/scene-full-epoch-v1/pilot-005000/000-iso6400-independent-role0-comparison.png) ·
[Exact-flat comparison](images/scene-full-epoch-v1/pilot-005000/000-iso6400-independent-role2-comparison.png).

![Limburg Cathedral, noisy, spatial 5k and exact GT](images/scene-full-epoch-v1/pilot-005000/001-iso6400-independent-role0-triplet.png)

Limburg Cathedral, query `[22,250]`, BGGR. Both arms restore the arch
contours and lose fine surface and window-edge detail.
[Full comparison](images/scene-full-epoch-v1/pilot-005000/001-iso6400-independent-role0-comparison.png) ·
[Exact-flat comparison](images/scene-full-epoch-v1/pilot-005000/001-iso6400-independent-role2-comparison.png).
The comparable full427 photo and measured camera panels are scheduled
for the full endpoints.

### Standing GFX100S at update 5,000

Both intermediate EMAs keep the sky smooth and retain both directions
of the coarse fence. Neither has a visible gain in coarse crossings.
Thin building lines and small leaf edges remain soft. The nominal
profile leaves most of the fine cab mesh faint. The transferred
DSCF3879 profile leaves both diagonal families faintly visible in
the right crop, with incomplete crossings and mottled underlying
paint. Both left and right crops and both camera JPEGs were reviewed.
The ISO100 AHD renders and JPEGs are independent qualitative references.

The spatial and local outputs differ by 2.08 DN16 camera-RGB RMS in
the sky, 8.45 in the coarse fence and 2.52–4.14 in the four cab views.
The comparison uses identical saved RAW, noise and rendering. CPU IEEE
FP32 inference on the ten archived observations took 265.47 s local
and 277.44 s spatial. Main views use DSCF3879/3880, native ROI `[176,176,160,160]` in
512-pixel queries, nominal shot/read `0.00128/6.5536e-6`, and
display exposure ×4. Cab views use DSCF3842/3835, native ROIs
`[206,229,160,160]` and `[426,189,160,160]` in a 768-pixel query,
with display exposure ×16. The transferred shot/read profile is
`0.0014635775921166604/1.0715704128646712e-6`.

The first renderer stopped at its output-path check. The corrected
renderer uses the same completed predictions and writes inside the
frozen worker directory. Both logs and the corrected render receipt
are included in the archive.
[Native review and provenance](results/scene-full-epoch-v1/matched-005000-standing.json) ·
[Collection and renderer evidence](results/scene-full-epoch-v1/matched-005000-standing.tar.xz) ·
[Sky](images/scene-full-epoch-v1/standing-005000/main-overcast-sky-main-overcast-sky.png) ·
[Building](images/scene-full-epoch-v1/standing-005000/main-building-detail-main-building-detail.png) ·
[Foliage](images/scene-full-epoch-v1/standing-005000/main-foliage-main-foliage.png) ·
[Coarse fence](images/scene-full-epoch-v1/standing-005000/main-chain-link-fence-main-chain-link-fence.png).

| Cab profile | Native views |
| --- | --- |
| Nominal | [Left](images/scene-full-epoch-v1/standing-005000/mesh-nominal-fine-green-mesh-left.png) · [Right](images/scene-full-epoch-v1/standing-005000/mesh-nominal-fine-green-mesh-right.png) |
| Transferred | [Left](images/scene-full-epoch-v1/standing-005000/mesh-profile3879-fine-green-mesh-left.png) · [Right](images/scene-full-epoch-v1/standing-005000/mesh-profile3879-fine-green-mesh-right.png) |
