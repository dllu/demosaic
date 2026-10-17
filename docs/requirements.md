# Completion evidence

The objective is the complete project in `PROMPT.md`, including trained quality,
not just software that executes. This checklist records the evidence required.

| Requirement | Evidence needed | Current state |
| --- | --- | --- |
| Modern method and DINOv3 recommendation | Primary-source research, architecture rationale, licensed pretrained backbone and ablation | Official pinned weights; an earlier architecture's matched 20k-step ablation has a small positive gain on 427 photos. The current architecture’s [completed fresh no-context/S/B comparison through 10,000 updates](fresh-dino-capacity-10k-review.md) finds no photographic context gain. The [completed ConvNeXt10k review](dino-convnext-pyramid-v58-10k-review.md) ties no-context on photo mean with mixed paired-real scores. No consistent mature context advantage or SOTA is established |
| Free, broad training data | Source attribution manifest, content-grouped held-out split, real corpus training | Active frozen Commons: 40,170 train / 2,303 val / 2,255 untouched test / 4 excluded. The reviewed4× extension has52,536 train; its V50 first gate was not promoted. The [completed next extension](commons-incoming-v3.md) reaches66,934 train at8× and4×, adding14,398 sources with full hash/metadata/area-consistency checks and unchanged holdouts. It stays separate from the active model. The [larger native extension](public-raw-expansion-v2.md) freezes128 captures/106 declared scene groups. Finite identity screening and spot checks do not establish complete scene recognition or a trained gain |
| 8×8 binning with additional precision | Linear-light float averaging and >8-bit cache, numerical tests | Implemented and tested; all 44732 eligible licensed sources prepared |
| Geometry, optical blur, exposure, synthetic fine detail | Executable data augmentation and inspected samples | Implemented. Complete 4×→geometry/PSF→2× Commons/native targets improve full-photo PSNR by .50990 dB in the matched V34 trial; original 8× validation remains fixed |
| Physical Bayer noise across cameras and ISO | Electron-domain Poisson/read noise, metadata and tests | Moment-tested simulation, conservative single-image estimates on three cameras; dedicated calibration still missing |
| 16-bit photos and personal cameras | Native RAW metadata/CFA handling, 16-bit output, read-only photo source, real-camera examples | All four cameras loaded; GFX100S 102 MP RGB16 outputs and other-camera crops verified; final quality pending |
| State-of-the-art quality, substantially better than RawNIND | Reproducible held-out numerical results and qualitative comparisons, including clipping boundaries, texture and shadows | Unmet. The fresh no-context10k arm reaches full42735.55039/.961097 but has a [fabric color regression](fresh-color-mean-diagnostic.md). ViT-S/B do not beat its photo mean; ConvNeXt10k ties it at35.54954/.961229 and has [selected saturated-flat errors](mature-color-flat-review.md). The [completed wider-palette4k review](wide-flat-palette-full4k-review.md) reaches35.66428/.961908 on427 photos, with a +.02054dB matched photo gain and stronger high-saturation groups, but persistent moderate-saturation errors and paired-real tradeoffs. V43 step2000 remains the README experimental reference; fine foliage/fabric stays soft. Broad real superiority and protected-final scoring remain |
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
The earlier precision/adapter source passed **379 tests in40.18s**, including
the explicit middle-skip precision control and prior identity/diagnostic checks. The optional DINO
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
[low-rank option](dino-low-rank-adaptation.md) is CPU/GPU-verified; its first
[trained V49 gate](dino-lora-v49-review.md) is now rejected.

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
all-CFA/noise/precision/checkpoint checks pass. Its
[completed matched review](camera-centering-v47-v48-review.md) lowers known/unseen
primary and photo/procedural sRGB PSNR, so both arms stop at1000 updates.
The [completed V43 first-gate review](native-v43-1k-review.md) now finds modest
positive unseen-primary/photo gains versus both matched controls. All33 logged
shared Commons/paired hashes match; ten native triplets and both full RGB16 files
verify. The larger native corpus becomes the next data recipe and V43 the current
experimental reference, with the parent-primary tradeoff and single-seed limits
explicit. The stable first-gate model alias and README crops are updated.

The optional DINO low-rank adapters complete their first
[matched training gate](dino-lora-v49-review.md), reusing V47 after source and
shared observation checks. They regress and stop at1000. The independent
[Commons extension](commons-incoming-v2.md) has10,558 newly reviewed training
sources; matching4× caches are now complete. V49 retained its old data;
V50 is the new data-only trial. Neither corpus size alone establishes a gain.

The [V49 rank4 review](dino-lora-v49-review.md) finishes with all41 shared
observations exact. Unseen primary/photo PSNR fall, so V49 stops at1000.
Twenty native comparisons, two full102MP RGB16 files and actual-trained
weak-signal CUDA checks verify. The larger Commons membership is the next
data-only trial; original frozen DINO remains.

The [V50 corpus first gate](commons-expanded-v50-review.md) loses known-primary/
photo PSNR and stops at1000 without promoting the new data recipe. Its20 native
comparisons and two full RGB16 outputs verify. Fresh Gaussian-initialized
S/B/no-context trials now have [genuine CPU/GPU preflights](fresh-dino-capacity.md).
They explicitly match middle-skip precision: a zero DINO offset had promoted
BF16 features toFP32, an arithmetic confound for an otherwise absent branch.
Legacy defaults/current checkpoints are preserved. The
[first1000 trained comparison](fresh-dino-capacity-1k-review.md) is complete:
all41 logged observations match,50 native triplets and ten full RGB16 files
verify. No-context leads unseen primary/photo; B improves photo versus S but
neither beats no context. No promotion; continue the matched arms before a
convergence decision. Current-architecture capacity benefit remains unproven.

The [full427 ADC-only correction](adc-cfa-projection-full427.md) improves photo
PSNR by.52882dB and SSIM by.003923, while procedural SSIM falls. Its optional
inference flag defaults off and activates only for explicit shot=read=0. The
V52 export preserves all V43 step2000 EMA tensors. CPU compatibility and actual
pinned-weight preflight pass; all-condition/CUDA/real checks remain pending.
This supplies no real-noise gain and does not repair the broad SOTA deficit.

A separate [paired-RAW quarantine](paired-extension-quarantine.md) selects59 new
scene candidates/231 files/11.03GB without relaxing train32. Acquisition runs in
frozen source; the actual two-scene identity/alignment pilot verifies36 crops.
Both references are screened against cached protected scenes and Commons
val/test. Screen/preparation successes retain quarantine; content, motion,
reference sharpness and a reviewed admission contract remain before training.

The [fresh matched3000 review](fresh-dino-capacity-3k-review.md) completes with
all122 logged observations equal,50 native triplets and ten full RGB16 files.
No-context leads photo and known/unseen primary; B improves photo/procedural over
S but no branch replaces V43. Classical/RawNIND baselines replay62,020 metric
cases exactly across gates. One seed/3000 updates does not establish convergence
or a universal foundation effect. Protected-final scoring remains closed.

The reviewed [paired-data extension](paired-extension-quarantine.md) preserves
all64 legacy pairs and adds102 from51 new publisher IDs, grouping repeated
views:83 scene IDs/71 groups/166 pairs/1492 crops. The active-display series and
seven identity flags remain quarantined. V53/V54 now train a matched data-only
comparison from retained V43 after451 CUDA tests and genuine B16 paired preflight.
No expanded-data model is promoted before the complete quality/native review.

The [V52 actual-export review](adc-projection-v52-review.md) completes86,828
synthetic cases, real known/unseen and full GFX. Seven-condition photo+.075545dB
comes solely from ADC-only data; all10,632 positive-noise synthetic cases/162
paired metrics and full GFX RGB16 pixels remain exact. Procedural SSIM falls
slightly. This optional policy supplies no real-noise improvement; original
aliases remain fixed. New training quality and the broad goal are still open.

The [complete V53/V54 4,000-step review](paired-expansion-v53-v54-4k-review.md)
does not sustain the expanded paired corpus's early photographic advantage.
The corpus stays opt-in. After 472 frozen-source CUDA tests and a genuine-parent
preflight, [V55's weak-texture first gate](weak-texture-v55-review.md) loses photo
and known-camera primary means, with mixed carrier response and no clear native
advantage. It stops at 1,000 without promotion. All 46 native triplets, eight
full GFX RGB16 files, 62,020 baseline and 12,404 matched-control replay cases
verify. V43 step 2,000 and its README crops remain the experimental reference.
These finite schedules do not establish convergence or a universal data effect.

The [optional DINO input adapter](dino-input-adaptation.md) passes the complete
current CUDA-enabled suite (**483 tests in 47.39 s**) and genuine-parent identity,
gradient and portable-load checks. The [matched V56 first gate](dino-input-v56-review.md)
finishes from the same initializer/data as V54 but loses photo/known primary
without a clear native advantage. It stops without promotion. All 41 logged
inputs/final RNG states match; 46 native triplets and eight RGB16 files verify.
Engineering validation remains separate from quality evidence.
A [CPU-only resume audit](results/fresh-dino-capacity-10k-resume-audit.json) also
verifies intact original no-context/S/B step 3,000 states and their unfinished
10,000-step schedules. A same-source V54 replay takes priority after V56 review,
to measure procedural repeatability without treating source intervals as
training-seed uncertainty. Broad quality/SOTA and speed requirements remain open.

The [completed V57 replay](control-replay-v57-review.md) demonstrates observed
procedural variation even with matching source/configuration,41 logged inputs
and final RNG states: photo−0.04346dB and known primary−0.05946dB. One replay
does not estimate seed variance or isolate the cause. The original fresh
no-context/S/B schedules now [resume toward10,000](fresh-dino-capacity-10k.md)
with complete state and unchanged original source/data/compute policy.

The [additional personal-camera check](cross-camera-qualitative.md) caches Q2,
Sony a7RII and GFX50R originals locally, fixes missing explicit noise conditioning
in the old comparison helper, and verifies12 native triplets plus18 float32
context outputs from actual V43 GPU execution. These are512-context development
comparisons without clean references or pixelwise scores; they do not establish
broad superiority or full-frame quality on those three captures.

The optional [DINOv3 ConvNeXt pyramid](dino-convnext-pyramid.md) adds finer frozen
feature grids and fusion at three CNN resolutions. Genuine pinned weights are
cached; [complete-state CPU restart](results/dino-convnext-pyramid-cpu-restart.json)
matches four uninterrupted updates with a 2+2 restart through Commons/native/
paired domains. CUDA validation and trained quality remain. The prepared fresh
V58 recipe changes backbone and fusion together.
It does not change the running original no-context/S/B comparison or establish
a foundation-model benefit, convergence or SOTA.

The [completed CPU additional-camera check](cross-camera-none10k-cpu-review.md)
compares fresh no-context10k with V43 using the same FP32 inference. All 38 native
PNGs were inspected, including two fixed source examples with exact simulated
GT; 21 real float context arrays and shared pixels verify. The real methods stay
close, fine cords remain absent and a fabric color bias is visible in the fresh
model. No promotion or causal DINO/duration conclusion follows from this check;
the full matched S/B/GFX evaluation remains pending.

The [standing GFX CPU context check](gfx-none10k-cpu-context-review.md) adds all
four fixed regions for V43/no-context10k and both RawNIND calibrations. All 20
new native PNGs and 24 float arrays verify, with exact rerendering and accurately
labeled independent ISO100 references. Learned fence lines are more continuous
than RawNIND, while fine foliage remains soft and the learned models stay close.
This is not a new 102 MP output, reference score or promotion; full matched
GPU review is still pending.

The [wider smooth-palette trial](wide-flat-palette.md) is prepared to target
selected mature saturated-field failures. Legacy/default data is exact in CPU
checks and the genuine-parent complete-state restart passes. Genuine native256/batch16 CUDA
validation and all517 tests pass. The [completed first1k review](wide-flat-palette-first1k-review.md)
finds tied photo PSNR, mixed real/color results and persistent native detail loss.
Both original4k schedules will continue; this is not a model promotion or
completion of the quality requirement.

The [completed genuine Nonlocal Match-Filter reference review](nonlocal-reference-full-review.md)
adds full427, known4/our-unseen5, analytic, full102MP GFX and three-camera
comparisons. It has higher but uncertain paired means, lower synthetic scores
and a selected magenta flat-grid failure. All64 native sets,29 F32 contexts and
8 full RGB16 files pass integrity checks; source overlap for the external model
remains unproven. This comparator does not establish SOTA or broad real-photo
superiority for our model.

The [prospective hue grid](prospective-color-grid.md) adds1,176 completely
audited uniform-field observations, with fixed previews and a serialized GPU
queue. All4,704 predictions/28,224 metric fields and12 native triplets now pass
independent checks; all12 previews were viewed. Bright-field biases remain.
It is a finite color-consistency diagnostic, not evidence of a trained
quality gain, independent natural-scene generalization or completed SOTA.

The [final4k review queue](palette-final-review-preparation.md) now waits for
actual training/evaluation-owner exit. Complete first1k rechecks and a zero-CUDA
4,704-array reuse run verify its tooling, while final4k quality remains pending.
The [physical preprocessing diagnostic](physical-frontend-color-check.md)
finds much smaller uniform-field errors before the CNN than the learned bias;
it does not establish a training cause or a photographic correction.

The [signed RawForge JDD CPU pilot](rawforge-cpu-pilot.md) adds a recent joint
reference on two fixed photos and all four standing GFX contexts. Actual
publisher-input, tensor, scalar and native-panel checks pass, but its explicit
CPU device port still needs the queued original-export GPU comparison. These
selected examples and uncertain external training membership do not establish
SOTA, broad real superiority or completion of the quality requirement.

The [completed V65 RAW-head review](raw-kernel-warmup-v65-first1k-review.md)
and [matched phase-conditioned V66 review](raw-kernel-phase-v66-first1k-review.md)
verify the clean constant-color reconstruction invariant but show poor noise
removal. V66 reaches29.52620/.872886 on427 photos: +1.69373dB over V65, still
6.13809dB below mature V60. Procedural PSNR regresses. All26 V66 native previews
were viewed, including two exact-GT photo triplets and all four standing GFX
regions; grain remains prominent. Both full101.996MP RGB16 files and exact native
ROI checks verify, but shared-machine restoration/blending51.352s misses10s.
Neither model is promoted. Numerical invariance and low mean color bias do not
establish useful denoising or the requested real-photo superiority.

The [separate V67 joint stage](raw-kernel-phase-joint-v67.md) passed genuine
seven-update CPU restart and production-size CUDA checks before launch from
completed V66 EMA. All92 restoration tensors/32,931,920 parameters train; actual
DINO remains frozen. Original10,000-update schedule, stopped at2,000 for full
review. Phase head-only features stayed frozen; joint training is a hypothesis,
not evidence of a quality gain or convergence. Complete development/color/native/
GFX/artifact jobs are serialized behind verified actual owners. Protected-final
model scores remain unused. The original quality and speed goals remain open.

The [completed V67 first2k review](raw-kernel-phase-joint-v67-first2k-review.md)
finds photo32.33964/.927021, +2.81345dB over initialized V66 but3.32464dB below
mature V60. Known/unseen CFA improve6.07209/7.01233dB; all primary means remain
below V60. All26 native panels were viewed: less grain, but lost cords/soft detail
and strong weak-carrier attenuation persist. Hue RMSE improves while mean bias
increases versus V66. Independent state94/94/92,50,264 primary cases/48 comparisons,
896 analytic cases,1,176 hue predictions and full101.996MP RGB16/native checks
pass. Shared-machine52.042s misses10s. No promotion or convergence claim;8,000
original updates remain, requiring a verified isolated continuation before final
full review. SOTA and the requested large real-photo advantage remain unmet.

The [verified isolated continuation](raw-kernel-phase-joint-v67-full10k.md) now
finishes the original V67 budget with all2k evidence preserved. Actual full-size
resume checks restore model/EMA/92Adam/best/RNG exactly; original2001/2025 input
hashes/domains/LRs match production. Final10k quality/native review remains.
The [serial final-review queue](results/raw-kernel-phase-joint-v67-full10k-review-queue.json)
is now waiting behind successful training completion, with primary panels,
statistics/hue and CPU artifact stages. Actual native viewing and a quality
decision remain pending; no new model is promoted.
