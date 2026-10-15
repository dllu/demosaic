# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Official pinned weights; matched 20k-step ablation complete; small positive gain on 427 photos, not SOTA evidence |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | 44732 prepared/audited sources: 40170 train / 2303 val / 2255 untouched test / 4 excluded; V6 completed 100k steps. A separate 32-scene licensed paired RAW subset is verified; V11 mixed and V15/V16 refiner training completed 5k-step reviews. Complete scene separation is not guaranteed |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; all 44732 eligible licensed sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented; augmentation and artifact review ongoing |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Moment-tested simulation, conservative single-image estimates on three cameras; dedicated calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | All four cameras loaded; GFX100S 102 MP RGB16 outputs and other-camera crops verified; final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Unmet. V16's known/unseen real measured-CFA PSNR is 53.27466/53.07857, still 0.79/0.48 dB behind RawNIND. Full 427 synthetic PSNR/SSIM is 31.48800/0.923018; V6 retains the stronger synthetic PSNR. Native crops show remaining noise/detail loss. V17 coarse correction is not promoted; V18/V19 test joint tuning against a refiner-only control. Final quality/protected-test evaluation remain. |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | V6, V15 and V16 full 102 MP RGB16/ICC-sRGB16 outputs verified. V6 idle warmed 100 MP restoration 12.77 s; V16 complete GFX restoration 53.28 s under concurrent training, 0.804 GB peak CUDA (not total system memory). The 10-second target and final quality/speed gate remain unmet |
| Python/PyTorch/uv and shared-machine care | Locked environment, bounded memory, resumable training, measured GB10 operation | Implemented and verified; CPU restart equivalence and GB10 runs pass |
| Diary, concise README, detailed docs | Current reproducible commands, experiment records and limitations | Present and being updated |
| Commit and push meaningful progress | Git commits and successful remote pushes | Meaningful progress is committed and pushed regularly; see the Git history and diary |

Photo directories are read-only. All writes, downloads, temporary files and caches
must stay in this repository or `/mnt/external`. Do not modify `PROMPT.md`.
