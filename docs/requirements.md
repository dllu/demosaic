# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Official pinned weights; matched 20k-step ablation complete; small positive gain on 427 photos, not SOTA evidence |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | Active frozen corpus: 40,170 train / 2,303 val / 2,255 untouched test / 4 excluded. A separately audited extension adds 1,808 train sources and reserves 196 new holdout sources. A separate reviewed native extension adds six CC0 outdoor captures, giving59 captures/37 scenes; V37/V38 remain on53/31. Near-duplicate screening is not complete scene recognition |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; all 44732 eligible licensed sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented. Complete 4×→geometry/PSF→2× Commons/native targets improve full-photo PSNR by .50990 dB in the matched V34 trial; original 8× validation remains fixed |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Moment-tested simulation, conservative single-image estimates on three cameras; dedicated calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | All four cameras loaded; GFX100S 102 MP RGB16 outputs and other-camera crops verified; final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Unmet. V34 first1000 full427 synthetic PSNR/SSIM is 34.46662/.954201, +.50990 dB versus its matched old-order control. Expanded V36 has a similar photo mean but weaker procedural/unseen means. Real primary changes are small and uncertain; channel-calibrated RawNIND leads unseen auxiliary RGB/SSIM. GFX foliage remains soft and colored points remain despite more legible wire mesh. [Matched metrics and native crops](geometry-corpus-v34-v36-review.md). Protected-final remains unscored; matched DINO ablation of this architecture remains |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | V32/V35/V34/V36 and both RawNIND calibrations have full 102 MP RGB16/ICC-sRGB16 outputs; all twelve files verified. V34 restoration took 37.03 s, tile512/overlap64/batch4, shared machine, excluding decode/load/render/encoding. The 10-second target remains unmet. A packed-resolution architecture prototype is under throughput/quality testing |
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
Full 4× Commons preparation passed its complete-membership gate before V34
trained; native 4× targets retain the same 53 captures / 31 scenes.
[More Commons originals](commons-download.md) continue downloading with a 512 GiB
reserve. Their first separately frozen extension adds 1,808 training sources;
active experiments and all existing validation/test assignments stay fixed.
The [matched corpus/augmentation pilot](training-pipeline.md#matched-corpus-and-augmentation-pilot)
tests the 1,808-source extension separately from the geometry change.
[V35 first 1k](expanded-v35-1k-review.md) improves unseen primary PSNR by .04306 dB
versus V32, with a .06106 dB photographic-screen regression and no decisive GFX
gain. [Both step2000 reviews](corpus-v32-v35-2k-review.md) are now stopped after
mixed results: the expanded arm improves known means but loses unseen primary
versus its first1k. Both complete4× corpora are frozen after reusing26,314 caches.
V34/V36 first1000 and full427/full102MP reviews are complete and stopped.
[Nine public RAW samples](public-raw-pilot.md) retain their original quarantine.
Six reviewed sources have a separate opt-in native extension; the chart and two
clipped sources are excluded. Current architecture trials remain unchanged.
All **304 tests pass**; Ruff passes. Trained quality, protected-final evaluation
and the 10-second speed gate remain outstanding.


The [packed-resolution prototype](packed-rgb.md) retains all Bayer phases,
genuine DINO and IEEE FP32 physical reconstruction. Its completed batch16 sweep
finds2.34× training throughput with51% less CUDA allocation, but the matched
[V37/V38 real review](packed-v37-v38-first-review.md) rejects V38: substantial
grain and a10.12dB unseen primary loss. All41 logged observations match. Full427
confirms a3.75dB photo deficit; fullGFX took19.90s and all ten RGB16 files verify.
Neither a quality gain nor10-second inference is established. The full-resolution
model remains the working reference. V39 now tests the six-source native
extension separately, retaining V37's initialization, seed, batch and schedule.
