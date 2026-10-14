# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Research underway; official HF weights currently return 403 |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | 77,025 downloaded Commons images located |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; first 1024 sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented; augmentation and artifact review ongoing |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Implemented and moment-tested; measured camera calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | GFX100S 102 MP input/output verified; other cameras and final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Initial 61-crop synthetic comparison favors ours; broad/real quality unproven; highlight artifacts found |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | 100 MP warmed restoration 9.88 s; cold 102 MP RAW restoration 17.04 s, excluding encoding; final model/end-to-end gate pending |
| Python/PyTorch/uv and shared-machine care | Locked environment, bounded memory, resumable training, measured GB10 operation | Started |
| Diary, concise README, detailed docs | Current reproducible commands, experiment records and limitations | Present and being updated |
| Commit and push meaningful progress | Git commits and successful remote pushes | Initial pipeline pushed as 0cc6050; continuing |

Photo directories are read-only. All writes, downloads, temporary files and caches
must stay in this repository or `/mnt/external`. Do not modify `PROMPT.md`.
