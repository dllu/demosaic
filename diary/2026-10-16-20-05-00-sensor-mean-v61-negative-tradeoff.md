# Sensor-mean V61: color gain, accuracy/detail loss

Completed the first1k review of the .01 full-restoration loss trial. All41logged
step/domain/LR/input hashes match completed V60. Independent state/source/data
checks confirm the original4000 schedule, complete finite91model/91EMA/89AdamW
state and RNG. No more V61 training or promotion is planned.

V61−V60 photo PSNR−.214121dB, SSIM−.002761, known-CFA−.158063dB,
unseen-CFA−.266250dB. Source-bootstrap intervals all exclude zero. Procedural
PSNR+.445269 has a wide interval crossing zero and lower SSIM. Primary arithmetic
audits50,264rows/72comparisons. Saved classical controls retain their inherited
four-F32-ULP bound; no control-network reruns were needed.

The broad hue diagnostic improves high-noise/peak.9/sat.98 mean max-channel bias
.032886→.006903, maximum.121354→.028888. Moderate saturation still reaches.064378.
Weak level.18/contrast.02/period16 in-phase gain worsens.52060→.32090. Actual native
views retain missing parachute cords, soft GFX foliage/fence/truss, and soft Q2/
Sony detail. GFX50R has more texture than RawNIND but also grain. ISO100 is not GT.
Full101.996MP pass35.321s; two RGB16 TIFFs verified, speed target unmet.

Refactored the hue engine to accept independently validated model records while
retaining original owner guards. CPU replay matches all4704old rows/72groups/
12whole PNG hashes with no CUDA or inference. New hue execution reuses3528audited
parent/V60/nonlocal arrays and infers only1176V61 predictions. Independent
Torch64 checks28224fields, separate summary audit864scalars. Published35native
PNGs:26actually viewed now,9previously viewed whole-file-identical grid images.
Primary artifact audit verifies19PNGs/23F32contexts/2RGB16files; noisy/reference
pixels and transforms match saved V60 exactly. CPU32-case audit192fields/4PNGs.

The original primary controller failed after analytic inference due to its own
wrong expected672row assertion. Candidate+Malvar gives896rows. Preserved failed
status/source and completed panels; a distinct recovery ran only missing GFX,
other-camera and CPU-audit stages. Recovery completed and exited. Report:
docs/sensor-mean-v61-first1k-review.md; JSON SHA
f095e3467b11aedc4c7c12713e1274975adae69eec2f51a881e6864457d42d59.

Prepared a distinct .001 recipe from the same V58 initializer, original seed,
data and schedule. Actual CPU preflight passes exact4vs2+2whole-state restart and
input-hash matches across all domains; genuineCUDA/B16 checks are running. Keep
completed V60 as control. Larger corpus stays separate; protected-final closed.

Commons v4 producer also completed:10022success/2failed,126identity flags remain
quarantined,8872new training candidates; combined candidate75806. Full independent
cache/content review and matching4× remain before admission. Existing40170model
data unchanged. Downloader remains live; no duplicate jobs or cold originals.
