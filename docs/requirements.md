# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Official pinned weights; matched 20k-step ablation complete; small positive gain on 427 photos, not SOTA evidence |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | 24576 prepared/audited sources: 22059 train / 1262 val / 1254 untouched test / 1 excluded; broader preparation live; scene separation not guaranteed |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; more than 37k licensed sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented; augmentation and artifact review ongoing |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Moment-tested simulation, conservative single-image estimates on three cameras; dedicated calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | All four cameras loaded; GFX100S 102 MP RGB16 outputs and other-camera crops verified; final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Full 427-photo multi-condition suite favors ours overall, but loses shadows and high-noise SSIM; real perceptual win unproven; larger training started |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | 20k DINO warmed restoration 14.53 s, 0.803 GB CUDA; earlier non-DINO 9.34 s; both legacy precision, exclude decode/load/encode; new FP32/final gate pending |
| Python/PyTorch/uv and shared-machine care | Locked environment, bounded memory, resumable training, measured GB10 operation | Implemented and verified; CPU restart equivalence and GB10 runs pass |
| Diary, concise README, detailed docs | Current reproducible commands, experiment records and limitations | Present and being updated |
| Commit and push meaningful progress | Git commits and successful remote pushes | Repeated progress pushed through 11b732d; continuing |

Photo directories are read-only. All writes, downloads, temporary files and caches
must stay in this repository or `/mnt/external`. Do not modify `PROMPT.md`.
