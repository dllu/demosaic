# Main comparison and full-corpus variance prior

The paired suite completed on 427 common validation photos, 16 separate stress
examples, four Bayer patterns and seven conditions. V4 step16000 after DINO20k
scores 29.8542 dB rendered PSNR / 0.88549 SSIM versus RawNIND CFA-LS
26.6708 / 0.78717, and wins each condition's average in both metrics. V4 shadows
are 34.7677/0.87682 versus 33.5095/0.85244; ISO12800 is 28.1951/0.81240
versus 25.7948/0.75936. The earlier DINO20k is 29.0946/0.85265. These are
local synthetic-observation scores, not proof of global state of the art.

The smooth-only V5 trial ends at its planned 5000-step review point. It improves
flat-field bias but trails V4 by 0.07580 dB (paired source-bootstrap 95% interval
0.07173–0.08038 in V4's favor) and 0.002481 SSIM. The two paths have equal
nominal update counts since DINO20k but different optimizers/LR/data; no isolated
causal flat-fraction claim is made. Numeric records are in
`docs/results/main16k-vs-smooth5k.json`. Original full artifacts remain in
`/mnt/external/demosaic/evaluation/smooth-vs-main-36k-v1/`.

Low-noise detail still trailed Malvar, and recent GFX100S ISO3200 RAW crops
retained visible grain. A 16-photo RGGB pilot tested phase-wise local
variance-adaptive filtering before Malvar. A 7x7 window on each packed phase
outperformed 15/31 for noisy photographic detail. Added this as an independent
classical comparator and optional learned residual baseline. It uses known
variance, subtracts expected noise power, preserves zero-variance samples exactly,
and remains an approximate local prior near clipping/weak texture.

V6 uses all 40170 training sources from the audited full corpus, batch eight,
10% continuous smooth scenes, 20% detailed procedural draws and 10% independent
ADC-only noise draws. It initializes feature weights from frozen V4 step23000;
only RGB/mosaic heads reset to zero, making initial output equal the prior.
It retains genuine pinned frozen DINOv3 and multiscale noise modulation.
The first 5000-step trial is finite and reached 31.3982 dB/0.91846 on the small
balanced monitor. At step1000, a 0.01-level ISO1600-prior flat retains 0.260 of
bilinear sigma versus V5's 0.632 and RawNIND's 0.0356. Real night crops reduce
grain markedly, but some low-frequency color variation remains. Full held-out
quality and convergence remain required.

V4 was deliberately interrupted after validating a finite step30000 checkpoint;
its 100k schedule did not finish. Only our own PID was signaled, after verifying
command/cwd/UID. V6 completed its finite trial, then resumed the full 100k
schedule. Logs: `.cache/train-dino-prior-44732.log`; current run:
`/mnt/external/demosaic/runs/dino-prior-44732-v6/`.

V6 step1000 processed the full 8746x11662 GFX100S RAW into camera-linear RGB16
and ICC-tagged sRGB16 TIFFs. Tags, dimensions and thousands of values off an
8-bit grid were verified. Cold end-to-end time was 58.714 s, restoration 39.264 s,
with two concurrent training jobs; this proves capability, not idle speed.
Step5000's warmed 100 MP eager restoration, without other training active, took
12.767 s at 512/64 tiles, batch eight, peak allocated CUDA memory 0.820 GB.
Host image arrays and allocator reserves are additional memory.

Performance prototypes are not promoted: default Inductor gave 10.644 s but
changed outputs (random-tile mean error about 4.96e-4). Precision-cast emulation
reduced differences but batch16 was slower. A 256-pixel DINO-preview cap reached
10.76 s and still needs quality validation. cuDNN/batch tuning found full-DINO
batch4 at 11.72 s. Eager full-preview inference remains the established path.
The profiler shows substantial cost in copies, pointwise arithmetic and layer
normalization, beyond convolution. Further speed work must retain quality.

Fixed initialization provenance being dropped on resume, with warm-start and
legacy-metadata restart tests. Restored V6's verified initialization receipt from
its immutable step1000 checkpoint; metadata only, no active weights/RNG changes.
Inference now hashes the same opened checkpoint inode it loads, and future
benchmarks preserve immutable checkpoint snapshots. All 49 tests and lint/format
checks pass. No test images or personal photos were added to training, no source
photos modified, and no private images committed.
