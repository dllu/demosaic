# Augmentation order: full review complete

Completed the matched V32/V35/V34/V36 first1000 review on all427 photographic
validation sources plus16 procedural sources, seven conditions/four CFAs,
111636 rows including both RawNIND calibrations and three classical baselines.
V34's4× ->geometry/PSF at2× target ->area2 order gains **.50990dB** photo PSNR
over V32's8× ->geometry,95% source interval[+.47646,+.54728]. V36 gains.63571dB
over its corresponding V35 control[+.60200,+.67021]. Original8× validation
stays unchanged. This is a real evaluation gain in a one-training-seed pilot,
not proof of training-seed robustness or broad SOTA quality.

V34/V36 photographic means are34.46662/34.47578 and SSIM.954201/.954526. Their
.00916dB difference crosses zero. V36's procedural mean32.94333 trails V34's
33.18400, and its unseen real means also trail. Choose V34 as the next pilot's
parent; it is not evidence that more diverse data is generally unhelpful.
V34's real primary changes versus V32 are+.01696dB known and+.02112dB unseen,
both scene intervals crossing zero. Unseen AHD RGB+.15341dB/SSIM+.003598 also
cross zero; RawNIND-channel still leads auxiliary unseen means.

Training used complete frozen4× datasets, the original V30-step1000 EMA,
fresh AdamW/EMA, batch16, seed46, LR3e-5/planned3000 and unchanged domain mix.
All16 logged paired observations match between V32/V34/V36; all11 native
observations match between V34/V36. Source-module bytes, initializer and
validation match the old controls. New source-bundle15af15... includes the
intentionally changed native4× manifest. Both stop at the first1000 review.

Full GFX102MP output completed for all four neural models and both RawNIND gain
modes. All12 RGB16 TIFFs passed SHA/size,8746x11662x3,uint16/16bit/sample tags,
>256 sampled-code checks; all six sRGB files have ICC profiles. Timings in model
order:36.90/36.25/37.03/35.98/18.32/18.41s, tile512/overlap64/batch4, shared
machine, excluding decode/load/render/encoding. No10-second result.

Published44 native160px triplets: both new models' real/development/context and
full synthetic/full GFX, plus both RawNIND full synthetic/full GFX comparisons.
All PNG SHA/dimensions, shared metadata and exact noisy/reference panel bytes
checked across methods. Inspected fabric/building and foliage/fence. Wire mesh
is more legible than RawNIND-channel, but fine foliage/fabric are soft and a
colored point remains. Real references remain accurately labeled; no new GFX
or protected data in training/fitting. README now uses V34 full outputs.
Report: `docs/geometry-corpus-v34-v36-review.md`; full receipt under results.

Merged isolated packed prototype commit0cbf0f3 only after main full evaluation
and all TIFF verification completed. Its own imports stay in the separate
worktree. All292 existing/final-buffer tests plus15 targeted tests pass; Ruff
passes. Controller PID567918 waited for review PID443420 and began the matched
throughput benchmark at03:39:57UTC. First full-resolution batch16 measurement
is29.11 images/s; packed measurements and quality training remain pending.
Subsequent V37/V38 compare scale1/2 from the same V34 EMA, seed47, batch16,
fresh optimizers, complete4× sources and planned3000/stop1000. Every logged
observation must match; full real/full427/fullGFX evaluation is queued.

Commons originals continue downloading separately with512GiB reserve; frozen
training sets do not change. The goal remains active: decisive qualitative
superiority, robust final evaluation, DINO ablation and the speed target remain.
