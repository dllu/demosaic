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
2k, 12k and 25k states on eight photos, and at 50k on all 64. It compares
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
The native renderer now writes its output inside the frozen worker's
directory. The intermediate review verified that path, and the
corrected endpoint worker is waiting for the 50k checkpoints.
[Native collector recovery receipt](results/scene-full-epoch-v1/endpoint-native-recovery.json).

## Execution status

Both CUDA qualifications passed. Each initial zero-output model reproduced the
parent prediction exactly and both arms saw identical Bayer inputs and clean
targets. Both production arms completed eight updates using the same 16 photos
and 64 crops, including two exact-flat and five weak-texture scenes. The local
arm then restored its update-eight checkpoint and continued from scene index 16.
Long-run training and quality review are in progress. Both arms
have completed 2,500 updates, with verified matching inputs for 5,000
distinct scenes and 20,000 native queries each. The local worker reached
update 4,500 on its way to the 5,000 milestone before the runtime RAM
reserve stopped it. Its phase had no saved checkpoint. The controller
restarted from the verified 2,500 checkpoint and the first 942 replayed
scene records match the interrupted attempt byte for byte. Numerical and
native review remain complete through 2,000.
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
state. The last verified matched pair remains at update 2,500.
[Recovery controller](../scripts/resume_scene_full_epoch.py) ·
[First durable segment and original worker identity](results/scene-full-epoch-v1/segmented-recovery.json) ·
[Second failure and durable restart evidence](results/scene-full-epoch-v1/segmented-recovery.tar.xz).
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
