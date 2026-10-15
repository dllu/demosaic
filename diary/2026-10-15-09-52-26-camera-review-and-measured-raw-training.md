# Camera review and measured RAW training

Previous goal stage was progress: committed the real evaluation pipeline and
launched controlled trials. Rechecked authoritative processes this morning: V6
completed 100000 steps; V7/V8 reached their planned 5000-step review stops; the
corrected full synthetic comparison completed. No stalled jobs were restarted.

V6 full 427-photo synthetic PSNR/SSIM is 31.7410/0.92339; procedural sources score
30.9055/0.92494. Corrected signed-input RawNIND remains lower on that synthetic
protocol, but wins both real development sets. V7 broad camera coverage fixes the
M100 color cast: rendered PSNR 18.9351→35.0830 relative to V6 step51000. V8's 0.02
normalized loss improves real PSNR only ~0.13–0.15 dB while costing 0.5446 dB on
the full synthetic photo set and 0.5570 dB on procedural sources. Do not promote
that stronger loss. Both still retain much more flat-field noise than RawNIND.

V9/V10 now compare standardized local phase residual inputs against the same
V7 step5000 initialization with matched seed, data, optimizer and schedule.
New channels start at zero weights. Two initial launches mistakenly used a
placeholder path and exited before training; corrected launches are live.
All old checkpoint defaults remain unchanged; warm-start expansion preserves
camera/noise channel roles. Trials are unpromoted pending real/detail checks.

Acquired/prepared a separate fixed 32-scene paired training subset: 119 RAWs,
5.291 GB, 64 pairs, 576 crops, no rejections, four camera models. All published
checksums pass. Exact capture/scene separation from the 25 protected scenes is
verified, including all 214 protected capture SHA1s. A conservative perceptual
screen found no matches to 4558 Commons validation/test photos; arbitrary crops,
edits and related views can evade it. The existing Commons corpus contains three
NIND-labeled museum photos; their titles are different from the protected scenes,
but title checks alone do not prove scene separation.

Implemented real training with measured-CFA targets, reference masks, deterministic
draws and phase-correct dihedral augmentation. Only 4×4 AHD RGB means supply
auxiliary color supervision. Real data is kept separate from Commons; both
manifest hashes/source snapshots are recorded and resume changes are refused.
148 tests and Ruff pass, including CPU exact restart equivalence with paired data.

V11 has started from the frozen V7 EMA, 50% paired RAW / 50% Commons simulation,
original synthetic loss and architecture, LR3e-5, planned 20000 steps with a 5000
review stop. CUDA real-pair losses and gradients are finite. Quality is not yet
established. All official final test targets remain out of model selection.
