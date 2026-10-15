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
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Unmet. V16's known/unseen real measured-CFA PSNR is 53.27466/53.07857, still 0.79/0.48 dB behind RawNIND. A fixed eight-step stabilized RGB Gaussian prior reaches 53.81110/53.84615: −0.26/+0.28 dB versus RawNIND, with bootstrap intervals including zero and lower SSIM. GFX fence detail improves, but foliage softness and colored dots remain. See [the comparator review](stabilized-gaussian-review.md). Full 427 synthetic V16 PSNR/SSIM is 31.48800/0.923018; V6 retains the stronger synthetic PSNR. V17–V27 and independent gray-prior controls are unpromoted. Final quality/protected-test evaluation remain. |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | V6, V15 and V16 full 102 MP RGB16/ICC-sRGB16 outputs verified. V6 idle warmed 100 MP restoration 12.77 s; V16 new-pair 102 MP restoration 36.39 s with default FP32 refinement and 26.81 s with optional validated FP16 refinement, single successive shared-machine runs; 0.840/0.708 GB peak CUDA (not total system memory). The 10-second target and final quality/speed gate remain unmet |
| Python/PyTorch/uv and shared-machine care | Locked environment, bounded memory, resumable training, measured GB10 operation | Implemented and verified; CPU restart equivalence and GB10 runs pass |
| Diary, concise README, detailed docs | Current reproducible commands, experiment records and limitations | Present and being updated; comparator reports include native exact-GT synthetic triplets and independently labeled real references, matched foliage/fence, source/checkpoint hashes and noise/display settings |
| Commit and push meaningful progress | Git commits and successful remote pushes | Meaningful progress is committed and pushed regularly; see the Git history and diary |

Photo directories are read-only. All writes, downloads, temporary files and caches
must stay in this repository or `/mnt/external`. Do not modify `PROMPT.md`.

V28's [first 1k pretrained RGB/DINO review](pretrained-rgb-v28-review.md) adds
33.43530/.947856 on the same 16-photo synthetic screen (+1.01706 dB over V16),
real primary53.99180/53.62905 and verified full102MP RGB16 restoration in24.88s.
Known-camera rendered quality and both real SSIM means still trail RawNIND;
bootstrap intervals include zero for primary superiority. This is early
progress, not satisfaction of the quality/speed gates. Original5k training is
continuing; full427/protected-final evaluation and matched DINO ablation remain.
