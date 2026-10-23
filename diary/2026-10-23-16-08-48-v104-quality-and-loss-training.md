# Complete V104 quality review and start the matched loss trial

Recorded: 2026-10-23T16:08:48-07:00 (America/Los_Angeles).

The previous goal turn made progress in commit `4cf7476`: matched V111/V112
recipes, actual CPU/CUDA checks and owned reporting queues. This turn completes
and independently reviews original V104's seven evaluation stages and full-frame
exports. All original training/evaluation/export owners exit successfully.

Full427 photographic PSNR rises36.679510→36.800846dB, +.121336 with a
source-bootstrap95% interval[+.117047,+.125735].424/427 source means and
11,815/11,956 cases improve;137 cases regress and4 tie. All427 source SSIM and
gradient means improve, and420 chroma means improve. All seven condition means
rise. Independently rebuild all86,828 photo/procedural rows;16 procedural
sources remain separate. Every original V102 metric on all12,404 cases replays
exactly. The archived photo-only result remains unchanged.

Known4 measured-CFA PSNR rises54.237088→54.266062, +.028973dB with3/4 scenes
improving. Unseen5 falls53.971775→53.917003, −.054771dB with2/5 improving;
Coulicoco drops.20550dB. Both small-scene bootstrap intervals include zero.
Rebuild all1,134 camera rows and scene-balanced means, reproducing every earlier
V102 camera case exactly. AHD RGB remains auxiliary and is not exact GT.
[Primary statistics](../docs/results/v104-reviewed-corpus-primary-statistics-v1.json).

The color check exposes a tradeoff that the overall photographic gain must not
hide. ADC maximum absolute camera-channel mean bias rises59.23→1218.06DN16;
means rise10.04→14.46DN. High-noise mean/p95/max improve. Independently rehash
all2,352 saved float predictions and1,176 observation archives, and recompute
all six metric fields in NumPy64. The worst ADC case is bright yellow,
hue45/saturation.98/peak.9, RGGB, with a+.018586 green offset. Add this posthoc
worst case for both models to the native color board, without new inference.
Rebuild all1,344 analytic texture rows and grouped statistics. High-noise
period16 gain rises.49887→.60487; period8 rises.02135→.05945, while residual
energy also rises and the fine carrier remains largely absent.
[Diagnostic evidence](../docs/results/v104-reviewed-corpus-diagnostics-v1.json).

Rehash and reopen all six current101.996MP linear/sRGB RGB16 TIFFs at
8746×11662×3 uint16. Preserve the original writer's sampled quantization checks
without claiming a whole-image learned-precision bound. New shared-machine
IEEE FP32/B4/tile512/overlap64 inference/blending takes168.20s V102,168.73s V104,
17.40s RawNIND, excluding loading/export. This is separate from earlier timings,
not a speed optimization or the100MP/10s target.
[Full-frame evidence](../docs/results/v104-reviewed-corpus-fullframe-v1.json).

Actually view all88 new native cells at original resolution:10 photo,20 camera,
12 texture,16 color and30 GFX. View all three resized full-frame overviews and
the final PSNR figure. Preserve all crop pixels and common observations/display.
Fabric cords, fine weave/foliage and saturated-sign structure remain soft.
V102/V104 remain close in real captures, with clearer geometry than RawNIND.
DSCF3880 remains a separate f/5.6 qualitative reference, not GT. The earlier60
material cells and their immutable receipts remain separate.

Select V104 as the working baseline for positive-noise captures and continued
training, while retaining V102 for lower ADC bias and its higher unseen-camera
mean. Update the README, model/usage guides, camera/GFX galleries, quality/data
pages and current DNG example. Keep the two V104 material triplets and replace
the README's GFX foliage/fence triplets with completed V104 full-frame crops.
Preserve the old selector bytes, reports and earlier galleries. The current
choice describes useful gains and weaknesses rather than requiring every metric
to improve. [Completed review and presentation snapshots](../docs/results/v104-reviewed-corpus-quality-complete-v1.json).

Extend the history renderer to permit explicitly declared completed metrics
without fabricated values for pending panels; older complete studies still fail
if a required panel disappears. Seven focused tests and Ruff checks pass.
Actually render44 photo points with43 known/unseen points, preserve that snapshot,
then backfill completed camera scores to44 each. All43 earlier point records
remain exact. Rebuild and view PNG/SVG/PDF with the V104 reference.

The initial next-training controller fails before any production optimizer update:
it expects `child` in terminal export status, but that schema intentionally
retains the owner only in the immutable result. Preserve its source/log/status
and all three dependent failed queues. Standard preparation binds that exact
completed result owner in new v2 roots. The corrected controller adopts the four
successful source/config-equivalent smokes without repetition and starts fresh
V111. All original recipe/preparation bytes remain unchanged; actual v2 run
paths and source configuration are recorded explicitly. V111's first real loss,
gradient and input hash replay the CUDA fixture exactly. All three domains execute.
A read-only health snapshot at1000 updates verifies91 finite model/EMA tensors
and89 finite Adam states, all step1000, with the intended source/manifest/parent.
This is health evidence, not intermediate image evaluation or endpoint selection.
V112 .0003 follows the .001 control at the same fixed20k budget.
[Actual corrected production launch](../docs/results/v104-loss-scale-training-started-v2.json).

The full project goal remains active: real fine-detail quality and broad SOTA
claims remain unresolved,100MP/10s is unmet, and V111/V112 have no completed
production quality result. Quality remains the priority.

Final publication verification passes142 receipt reference entries,158 unique
file hashes, all50 native triplet PNGs and88 saved board cells, five active frozen
plans and six unchanged original plans. Five exact live handles are verified.
The final link pass checks613 local links/fragments across23 changed/new
Markdown files. Three stale earlier download-section links now point directly
to their preserved source/worker receipts. Seven targeted history tests and
Ruff checks pass. The current source-bound V111 training continues.
