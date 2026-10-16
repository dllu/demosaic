# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Official pinned weights; matched 20k-step ablation complete; small positive gain on 427 photos, not SOTA evidence |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | Active frozen corpus: 40,170 train / 2,303 val / 2,255 untouched test / 4 excluded. A separately audited extension adds 1,808 train sources and reserves 196 new holdout sources; current trials remain unchanged. Separate licensed paired/native RAW train subsets are verified. Near-duplicate screening is not complete scene recognition |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; all 44732 eligible licensed sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented, including optional 4×→geometry/PSF→2× for Commons/native targets; full Commons 4× preparation and matched trained-quality comparison pending |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Moment-tested simulation, conservative single-image estimates on three cameras; dedicated calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | All four cameras loaded; GFX100S 102 MP RGB16 outputs and other-camera crops verified; final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Unmet. V32 step1000 full427 synthetic PSNR/SSIM is 33.95672/.950119, +.17289 dB versus V30. V33 improves our rendered real-development means, but channel-calibrated RawNIND leads all three unseen-camera means. GFX foliage remains soft, mesh irregular and colored points remain. [Matched metrics and native crops](low-lr-paired-v32-v33-review.md). Protected-final remains unscored; matched DINO ablation of this architecture remains |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | V30/V32/V33/RawNIND full 102 MP RGB16/ICC-sRGB16 outputs and all eight file hashes verified. V32/V33 restoration took 35.42/35.77 s, tile512/overlap64/batch4, successive shared-machine runs excluding decode/load/render/encoding. The 10-second target and final quality/speed gate remain unmet |
| Python/PyTorch/uv and shared-machine care | Locked environment, bounded memory, resumable training, measured GB10 operation | Implemented and verified; CPU restart equivalence and GB10 runs pass |
| Diary, concise README, detailed docs | Current reproducible commands, experiment records and limitations | Present and being updated; comparator reports include native exact-GT synthetic triplets and independently labeled real references, matched foliage/fence, source/checkpoint hashes and noise/display settings |
| Commit and push meaningful progress | Git commits and successful remote pushes | Meaningful progress is committed and pushed regularly; see the Git history and diary |

Photo directories are read-only. All writes, downloads, temporary files and caches
must stay in this repository or `/mnt/external`. Do not modify `PROMPT.md`.

The [completed V32/V33 matched review](low-lr-paired-v32-v33-review.md) includes
real development, all 427 synthetic photographs, native exact-GT triplets and
full-frame GFX foliage/fence comparisons. Both arms use the same V30 EMA with
fresh optimizers, batch 16 and LR 3e-5. V32 is the stronger synthetic reference;
V33's [step-2000 gate](paired50-v33-2k-review.md) is now complete and stopped
after mixed results. This does not establish broad real-camera superiority or
a decisive qualitative gain.

The [training pipeline](training-pipeline.md) implements augmentation before
the last reduction and avoids discarded Commons batches. A batch sweep selects
16 for throughput/memory balance. [Invariant Poisson-grid reuse](expectation-grid-performance.md)
adds about 11% measured batch-16 throughput with bitwise-identical tables.
Full 4× Commons preparation must pass a complete-membership gate before V34
trains; native 4× targets already retain the same 53 captures / 31 scenes.
[More Commons originals](commons-download.md) continue downloading with a 512 GiB
reserve. Their first separately frozen extension adds 1,808 training sources;
active experiments and all existing validation/test assignments stay fixed.
The [matched corpus/augmentation pilot](training-pipeline.md#matched-corpus-and-augmentation-pilot)
tests the 1,808-source extension separately from the geometry change.
[V35 first 1k](expanded-v35-1k-review.md) improves unseen primary PSNR by .04306 dB
versus V32, with a .06106 dB photographic-screen regression and no decisive GFX
gain. Both continue to the matched step 2000 gate; V34/V36 remain gated on complete
frozen 4× data. All **271 software
tests pass**. Trained quality, protected-final evaluation
and the 10-second speed gate remain outstanding.
