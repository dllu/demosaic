# Local RAW attention from the V143 parent

**V144's control is complete; V145's attention training and the paired quality
comparison remain in progress.** Both arms have1,000-update horizons.
V144 continues the V1435k EMA with its existing architecture. V145 adds the
implemented [local RAW attention branch](raw-spatial-features.md), with a
separate learning rate for its new weights. This tests a direct spatial path
after the completed [V140 memory pilot](v140-standalone-pilot.md) made almost
no useful image change. It does not resume the unstarted V132 experiment.

The branch mixes signed sensor differences in two shifted local windows and
supplies native stem features. It has 23 tensors and 22,664 parameters. Unlike
the memory-only branch, its content need not pass through 64 shared latent
slots. Exact constant inputs give zero branch features after learning; noisy
flats and the jointly trained trunk still require measured checks.

Both arms use seed144 and the same V143 training data, loss and noise recipe:
native256/B16/BF16, 90,782 photos/27 reviewed regions, 50% reviewed quota,
zero optical PSF, crossed-line/empty source fraction .10 within the .15 weak
quota, pixel/gradient Charbonnier epsilon .0003/.00003. The trunk uses LR1e−5,
warmup100 and a fresh cosine1k schedule. V145's branch uses 100× that rate,
peaking at1e−3. Both official DINOv3 encoders remain frozen. The comparison
combines architecture and branch-rate changes; it does not isolate learning rate.

[V144 recipe](../configs/quality-v143-spatial-control-v144.yaml) ·
[V145 recipe](../configs/quality-v143-spatial-attention-v145.yaml) ·
[Training driver](../scripts/train_v143_spatial_trial.py) ·
[Review driver](../scripts/review_v143_spatial_trial.py).

Genuine CPU128/B1/FP32 and CUDA256/B16/BF16 checks execute 16 updates and two
resumed updates per arm before production. They compare the initial outputs
and all clean/noisy batch hashes, check finite model/EMA/Adam states and reject
a changed branch rate on resume. New optimizer groups preserve the branch
multiplier through scheduling and Adam restore. Historical configurations keep
their original single-rate behavior. Each production arm starts freshly from
V143, with a12GiB CUDA allocator cap and32GB runtime RAM floor.

**All four genuine CPU/CUDA checks pass**, including all18 matched clean/noisy
batches and identical initial outputs per device. The72 discarded updates/root/
encoder calls cover612 target contexts. V145's CUDA peak is9,047,288,320 bytes.
The independent state-only audit reopens all eight16/18-update checkpoints,
verifies finite state, all81 trained source modules and actual89/23 optimizer
groups/rates, and constructs no model. The broad feature/optimizer checks cover
174 cases after correcting one test's exact floating-point equality; the separate
review/optimizer compatibility run passes158 cases, overlapping15 new tests:
317 distinct cases verified after correction. [Checks, byte-preserved logs and
independent audits](results/v144-v145-spatial-setup-v1.json).

V144 completed its1,000 updates and64 validation forwards, preserving its
finite91-tensor model/EMA and89 Adam states. Its102-input primary numeric/pixel
audits and all faint/flat/JPEG stages pass. The original review controller then
stopped on a completion-record filename error: the flat auditor writes
`independent-flat-audit-v1.json`. A separately frozen replacement adopts the
completed150-input V144 review without replay and prepares V145 once. Original
failure/status/source bytes remain preserved; training continues unchanged.
[Recovery plan](results/v144-v145-review-recovery-plan-v2.json).
Fresh V145 production is running. The paired endpoint quality comparison is pending.

Each endpoint has a fixed review of102 retained inputs and48 exact analytic
flats. It reuses V120/V143 predictions; V145 also reuses V144. The review includes
ordinary and weak photos, faint ADC detail, sky/building/foliage/chain-link in
DSCF3879/3880, the fine green mesh in DSCF3842/3835 under both noise priors,
and both camera JPEGs. Native160 crops share coordinates and transforms,
including at least two noisy/restored/exact synthetic-GT triplets. Independent
ISO100/AHD/JPEG and approximate binned references are not exact GT.

Training and review source snapshots are frozen independently. The review uses
cached arrays and makes no new noise draws, source-drive opens or RAW decodes.
Both protected scene families and siblings remain excluded from training;
`/mnt/dataz` is unavailable and is not used. Full427-photo, camera/color,
full-frame and speed qualification remain outside this pilot. V120 remains the
general recommendation; this experiment does not change inference defaults.

The separate [photographic supplement](spatial-photo-supplement.md) adds128
photo contexts from16 validation sources, including eight new organic-detail
images. Its measured V143 baseline has mean faint/dark organic DCT response
.151/.399, with visibly missing fine texture. All24 native baseline triplets
and independent metric/pixel checks are published. The supplement reuses64
parent predictions and declares320 additional root/DINO calls;64 parent calls
are complete. V144/V145 follow after both primary reviews. It adds64 new noise
observations without changing the original150-input reviews or training.
