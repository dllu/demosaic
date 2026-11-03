# Larger coherent RAW frequency pilot

Recorded: 2026-11-03T06:55:33-08:00 (America/Los_Angeles).

Completed V146: a fresh500-update V1435k frequency-only pilot, packed128/native256
Fourier windows and mesh/weak/synthetic Commons fractions.60/.65/.70. BranchLR.001,
warm100, native256/B16/BF16, seed146. Only3264 parameters/five tensors train; all91
parent model/EMA tensors and official frozen DINOv3 remain exact. CPU128B1 and
CUDA256B16 discarded16+2 checks pass, including scope/window resume rejection.
Window metadata defaults64 for old checkpoints; frame geometry changes reject
resume even though weight shapes match. 82 tests pass;15 new window cases.

Production completes500 updates/8000 targets/32 validation calls. Domain batches
are252 Commons,107 paired,141 native. Commons contains1246 present meshes,1183
empty meshes,418 smooth fields,209 weak textures,189 strong synthetics,787 photos.
Independent stateless replay matches all240 sampled Commons source records.
All500 input hashes are retained; first18 production inputs/initial outputs match
the discarded CUDA run. Five finite Adam states reach500; peak CUDA8752963584B.
CheckpointSHA ceb55cc938ad7950d61b3904c34a8cddc0b2ed299d61e3d210bb93cc592867e0.

Both raw and EMA weights were prospectively queued on694 reused inputs each:
512 mesh/empty,128 photo,48 flat,6 real GFX contexts. Sources are exact frozen82
modules, checked against the actual aggregate training snapshot. Actual new
root/DINO calls total1956=36smoke+500train+32validation+1388review. Reviews draw
no new noise or decode RAWs. Training uses its declared ordinary noise recipe.
Original RAFs/source drives and /mnt/dataz remain unopened; all work uses cached
arrays under repo/external. All owned jobs exited; no other project's jobs touched.

Result: no useful improvement. Present response .02202090→.02211809 EMA/
.02215646 raw (+.44%/.62%), while image RMS9.111243→9.116588/9.115914 worsens.
All256 absent cases change, addedRMS .326715/.316308DN16; this includes DC change
and is not alone proof of fabricated texture. All4 photo group mean/band errors
increase. Raw noisy-flat full256 spatial error falls.074% and whole512 sky
variation.32%, but EMA central160 flat error rises.058%. Do not mix full-context
and central metrics. Neither endpoint replaces V143 or the optional detail stage.

Actually viewed22 native figures via6 unscaled sheets: weak/strong procedural
mesh,4 repeated exact-GT triplets, absent field, all mainGFX sky/building/foliage/
chain-link, both extra green-mesh priors/windows/JPEGs,3 organic photos,2 flats.
No clear new lattice/feathers/moth scales; foliage stays painterly, grass soft.
Building/sky show no obvious new color blocks at these displays; noisy-flat
mottling persists. New JPEG panels are native sRGB8; RAWmesh is+4EV. Independent
ISO100/AHD/JPEG references remain accurately labeled notGT and are unscored.
Audits check2658 rows/16910 scalars/149 Decimal reductions/8832000 RGB channels.

Preserved two review-waiter corrections without model replay. First launcher
resolved the venv symlink to system Python and failed importing torch before
binding. Correct absolute venv launch then waited; preflight found source_sha256
is an aggregate string rather than a per-file mapping. Stopped only that owned
waiting process, preserved receipts, corrected a new waiter to hash actual saved
snapshot bytes and compare82 modules. CPU snapshot preflight verifies the fix.
Training and the predeclared endpoint/input queue remained unchanged.

Published22 native figures and an honest report; kept existing useful baselines.
Next diagnostic may test inference-only window256/native512 with the same
weights, clearly labeled untrained context transfer. No such transfer ran here.
Metadata check: native512 training at unchanged effectivebin8 would shrink
90782→1759 eligible train photos and leave0/27 current reviewed ROIs eligible.
Do not stretch caches, silently discard geometry, or claim matched source data.
Fine low-contrast/dark detail and clean noisy skies remain an active goal.
