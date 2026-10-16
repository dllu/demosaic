# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Official pinned weights; an earlier architecture's matched 20k-step ablation has a small positive gain on 427 photos. A trained ablation of the current pretrained-RGB architecture remains; SOTA is unproven |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | Active frozen Commons: 40,170 train / 2,303 val / 2,255 untouched test / 4 excluded; a separate extension adds 1,808 train and reserves 196 holdouts. The [larger native extension](public-raw-expansion-v2.md) freezes 128 captures/106 declared scene groups, adding 69 reviewed CC0 photos to the prior six. V43 is its matched trial; V37/V38 remain on53/31 and V39 on59/37. Finite screening/manual review is not complete scene recognition |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; all 44732 eligible licensed sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented. Complete 4×→geometry/PSF→2× Commons/native targets improve full-photo PSNR by .50990 dB in the matched V34 trial; original 8× validation remains fixed |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Moment-tested simulation, conservative single-image estimates on three cameras; dedicated calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | All four cameras loaded; GFX100S 102 MP RGB16 outputs and other-camera crops verified; final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Unmet. [V43 step 2000](native-corpus-2k-review.md) reaches full427 34.89934/.957126, gaining .08870 dB over matched V37 and .19536 dB over its first gate. Unseen primary improves .07632 dB versus its first gate, while AHD SSIM falls and procedural PSNR loses .56471 dB with large low-noise failures. V43 step2000 is the photographic experimental reference; fine foliage/fabric remains soft. Broad superiority, protected-final scoring and a current-architecture trained DINO ablation remain |
| 100 MP possible, target <10 s on GB10 | Actual 100 MP run, memory and timing; quality takes priority if speed misses | Full 102 MP RGB16/ICC outputs are independently verified for retained models and rejected packed variants. V42 is an unchanged-tensor V37 inference export with explicit hidden autocast; its complete quality/native-crop and repeated full-frame timing evidence is in the [review](hidden-autocast-v42-review.md). The 10-second target remains unmet. Packed V38/V40/V41 fail the quality gate |
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
The complete CUDA suite now passes **358 tests in 27.81 s**. The optional DINO
adapters pass genuine full-model BF16/FP16 initial-output equality, backward,
original-weight preservation and full-state training-resume checks.
[GPU receipt](results/dino-lora-gpu-preflight-v1.json). The
[current-pipeline batch sweep](current-pipeline-batch-sweep.md) is complete and
retains batch16 for controlled quality comparisons.
Trained quality, protected-final evaluation and the 10-second speed gate remain
outstanding.


The [packed-resolution prototype](packed-rgb.md) retains all Bayer phases,
genuine DINO and IEEE FP32 physical reconstruction. Its completed batch16 sweep
finds2.34× training throughput with51% less CUDA allocation, but the matched
[V37/V38 real review](packed-v37-v38-first-review.md) rejects V38: substantial
grain and a10.12dB unseen primary loss. All41 logged observations match. Full427
confirms a3.75dB photo deficit; fullGFX took19.90s and all ten RGB16 files verify.
Neither a quality gain nor10-second inference is established. The full-resolution
model remains the working reference. V39's
[completed six-source native review](native-v39-1k-review.md) retains V37's
initialization, seed, batch and schedule and finds small, uncertain real mean
gains with mixed synthetic results. No decisive overall gain is established.

The [V40/V41 detail-prior review](packed-detail-v40-v41-review.md) is complete:
much of V38's noise loss is repaired, but the full-photo deficit versus V37 is
still about 2.8 dB. A 10× phase-head LR does not close the gap. Neither is
promoted. The subsequent [V42 precision review](hidden-autocast-v42-review.md)
changes only the first hidden encoder's autocast policy, retaining V37's learned
tensors and FP32 native skip. Known/unseen primary and full-photo mean changes
are tiny; ten native triplets, actual-trained CUDA weak-detail checks and two
new full RGB16 outputs are verified. This is a compute-policy improvement,
not a new quality gain. Current-architecture trained DINO ablation and protected
final assessment still require a selected stronger model.

The [second native source review](public-raw-expansion-v2.md) verifies all 138
downloaded RAWs, decodes 131, retains 69 new photographic captures after clipping,
content and overlap review, and preserves the prior 53+6 targets. Both 4×/8×
datasets are frozen separately with exact source/cache/admission identities.
The [V43 recipe](../configs/dino-anchored-native-diverse-b16-v43.yaml) changes
only this native dataset against V37/V39; it retains full-resolution/precision
policy and other data. The first1000 training/full-review workflow is complete;
data admission and training loss alone do not establish a quality gain.

The [matched continuation to step2000](native-corpus-2k-review.md) is complete.
All 65 shared logged Commons/paired observations match. Its 30 native triplets
and six full RGB16 outputs are verified. V43 improves photographic and unseen
primary means versus its first gate, but regresses on low-noise procedural
sources and unseen AHD SSIM. All three arms stop at this gate pending failure
analysis. The README uses its photographic experimental checkpoint, with the
first1000 alias retained. A new batch sweep measures the actual current
4× Commons/native128 path, followed by completed adapter GPU checks. The
[fresh DINO presence/absence trial](fresh-dino-ablation.md) is prepared; the
[low-rank option](dino-low-rank-adaptation.md) is CPU/GPU-verified, not quality-trained.

The [selected low-noise failure diagnosis](native-low-noise-camera-diagnosis.md)
finds strong sensitivity to the learned WB/matrix projection. Native exact-GT
examples show a large color bias; zeroing only that input group recovers it on
the selected patterns, while anchor removal harms them and DINO removal is
mixed. This is an inference intervention, not a trained ablation. Classical
cases replay exactly; small neural replay differences remain explicitly marked
as failing the original strict tolerance. V46 exports only that weight-slice
change. Its [complete review](camera-projection-v46-review.md) finds photo and
procedural PSNR gains but known-camera accuracy loss, so it is not promoted.
The [camera-matrix centering experiment](camera-matrix-centering.md) instead
retains all metadata and preserves the parent's exact initial forward while
changing matrix optimization coordinates. All358 CUDA tests and genuine
all-CFA/noise/precision/checkpoint checks pass; matched trained quality is pending.
The [completed V43 first-gate review](native-v43-1k-review.md) now finds modest
positive unseen-primary/photo gains versus both matched controls. All33 logged
shared Commons/paired hashes match; ten native triplets and both full RGB16 files
verify. The larger native corpus becomes the next data recipe and V43 the current
experimental reference, with the parent-primary tradeoff and single-seed limits
explicit. The stable first-gate model alias and README crops are updated.
