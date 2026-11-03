# V147 loses weak detail and the gate limits damage

Recorded: 2026-11-03T 11:21:09-08:00 (America/Los_Angeles).

V147 completed the fixed 1,000 updates after continuing the original suspended
worker in memory. Both prospectively fixed raw/EMA endpoints ran on all 766
cached observations;32 new mixed controls also completed. The parent and official
DINO hashes stayed exact. All 12 Adam states reached 1,000 with finite weights/
moments and nonzero maximum gradients. CPU/CUDA RNG states match at checkpoints
250/500/750/1,000. All ten adopted smoke-prefix inputs and total losses match;
one FP32 gradient subterm differs by 9.3e-10, so no independent bit-exact full
trajectory is claimed.

Actual batches:357 mesh/106 weak/158 flat/164 mixed/215 photo. There are 4,000
unique observation IDs,740 present and 688 absent mesh targets. The 860 photo
examples use 453 unique sources,419 faint targets and 433 reviewed-ROI choices.
All 16 review-photo sources are outside the eligible pool and actual photo trace.
Procedural 512/photo 256 retains the intended binning/geometry without stretching.

The result is unhelpful for the requested weak-detail/quiet-region tradeoff.
Mesh response falls from .0220209 to .0202623/.0202942 raw/EMA (−7.99%/−7.84%).
Present-mesh RMS rises .379%/.409%; fresh 512 noisy-flat error rises .238–.345%.
All four photographic groups lose band gain and increase band error. Organic
dark full-image RMS improves only .0032%/.0038%, without convincing new native
structure. The strong-edge controls show a real small full-scene gain of .31–.42%,
while exact quiet-region error increases. Do not hide that gain or confuse it
with safe detail recovery.

Actually viewed all 50 main/mixed figures in 13 original-resolution sheets.
The faint synthetic mesh remains nearly absent; one stronger recipe retains one
family but not the crossing family. Main/extraGFX, both priors/windows/JPEGs,
stay near the parent: no clear new fine green lattice; foliage remains painterly.
Feathers, moth detail, grass/bark and actual 512 bird/branch remain soft. At 40×
diagnostic contrast, noisy flats and edge-adjacent quiet fields retain colored
mottle and slightly more fine grain. Exact ADC constants stay unchanged; that
structural invariant does not prove noisy-flat safety. Real ISO 100/AHD/JPEGs
remain qualitative and are not GT.

The near-uniformly small image-level support means (about .133 on mesh/photos)
suggested checking whether the local gate hid usable detail. Prepared a labeled
post-hoc intervention on the raw endpoint, all 766 cases, replacing only local
support with 1. All 766 learned-path replays are bit-exact to archived predictions;
weights, frequency gains, inputs and parents stay fixed. Mesh response falls
further to .0086952, full RMS grows to 10.35740 and blank spill rises from .62761
to 4.70598 DN16. Fresh 512 flat RMS grows to 21.26113/28.38856 at 6400/12800. All
four photo groups regress. This gate is limiting a poor frequency proposal.

Actually viewed the 14 intervention boards in four more native sheets. Full
support exposes false fine grid/grain on the exact noisy-flat fields and adds
grain/colored ripple in real mesh and feather crops without convincing recovered
true structure. The next change should address the estimator/supervision,
including learned phase combination; merely opening support or training this
same scalar proposal longer is not the next best experiment. This is evidence
about the trained pilot, not proof that all late spectral routes fail.

Published [the completed report](../docs/late-spectral-detail.md),64 byte-exact
native PNGs (including eight triplets),19 byte-exact evidence copies and new
source/trace indexes. Original 6.76MB full training trace/checkpoints/arrays remain
unchanged in the cache. Independent main reductions check 18,782 scalars/203
Decimal groups (max 4.55e-13); pixel checks cover 25,113,600 RGB channels, including
repeated triplet cells. All 14 recorded job owners and an exact-argument process
scan are terminal. Tracked calls excluding unit tests:1,032 parent/DINO (nested)
and 3,372 component, including the 766-call intervention. Main inputs were reused;
only 4,000 training observations and 32 new mixed controls were constructed.

V147 stays a research component. The current useful V143/explicit periodic
stage remains imperfect, and the user goal is still active. No RAW decode,
original-media access or `/mnt/dataz` access occurred. The historical preparation,
pause/resume and failed-preflight receipts remain intact.
