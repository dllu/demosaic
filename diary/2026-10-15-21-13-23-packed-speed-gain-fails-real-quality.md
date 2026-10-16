# Packed speed gain fails the first real gate

Completed ten throughput cases, after the preceding full geometry review had
finished. Batch16 ABBA means: full29.36 versus packed68.74 images/s,2.341×;
allocated CUDA6.95 versus3.40GB. Packed8/32/64 means64.25/69.30/66.46 images/s.
Batch32 gains only.81% over16 while using45% more memory;64 is slower and uses
9.31GB. Keep16 in both quality arms. Measurements include selected-domain
loading/degradation, genuine frozenDINO, CNN training, AdamW and EMA, exclude
8 warmup/startup/validation/serialization;30 measured steps/two repeats/shared
machine. Domain schedules match. This is training throughput, not inference
latency or quality. Full receipt: packed-rgb-throughput-v1.json.

V37/V38 both completed1000 updates from the same V34 EMA/seed47/fresh optimizer.
All41 logged observations match, source/initializer hashes match. V38 is rejected
at the real-development gate: known primary45.58580 versus54.27943 control;
unseen43.56215 versus53.67990. AHD RGB/SSIM also substantially regress. Inspected
native plate/chart examples: much of the fine grain survives. Full427/fullGFX
review remains live under controller567918; do not restart or assume its results.

An analytical basis-impulse diagnostic shows the identity detail bypass carries
58.03% of MHC Gaussian-noise power under unitWB/interior assumptions, even with
perfectly clean coarse RGB. Actual low-countGAT is approximate. The new small
phase head, fine-tuned at the shared3e-5 LR, did not remove enough of this burden.
Next candidate should test a noise-aware fine-detail prior and head optimization,
keeping ADC-only/native precision and exact output phases. Do not promote speed
as quality; keep V34 as the working reference. V37 itself has mixed continuation
effects, known primary+.03286 but unseen-.10674 versus its V34 parent.

Published the completed real review and12 native triplets, including two exact
syntheticGT160px triplets per new model from the first prescribed full-suite
sources. Hashes/dimensions/shared metadata and exact noisy/GT panel bytes checked.
Real AHD remains a reference, notGT. Full427 means/fullGFX timing are explicitly
pending at that first publication. The complete review subsequently finished:
V37 photo34.65497/.955273, +.18835dB over V34 [+.16031,+.21364]; V38
30.90134/.880821, -3.75363dB versus control [−3.85081,−3.65916]. All443 sources,
99,232 rows. Full GFX times35.54/34.33/19.90/18.24/18.12s for parent/control/
packed/Rawglobal/Rawchannel. All ten full RGB16 files passed independent full
hash/size, shape/dtype/bit-depth, sampled-code and ICC checks. Full native
foliage/fence confirms grain;32 published triplets include both RawNIND modes.
README stays on V34. Goal remains active: no SOTA/final gate or10s result.
