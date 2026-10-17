# Smaller sensor loss remains an unfavorable tradeoff

Completed V62 first1k review. Photo35.56006/.960947 versus V60 35.54917/.961343;
PSNR delta+.010886 has sourceCI crossing zero, SSIM−.000396 does not. Procedural
PSNR+.379150; knownCFA−.027050 has CI crossing zero, unseenCFA−.128072 does not.
V62 recovers much of V61's accuracy but does not improve the matched control.

High-noise/peak.9/sat.98 grid mean max-channel bias improves.032886→.018197,
but worst.103037 remains large; moderate saturation worst.096704. V61's stronger
loss has less bias but worse detail/accuracy. Weak period16 carrier gain.44277
versus V60.52060; dark carrier nearly absent. Native parachute cords, GFX mesh/
foliage/truss, Q2 rocks and Sony details remain deficient. GFX50R retains wall
texture versus RawNIND with grain. No clear native gain or general real superiority.

Stop V62 at1000 and do not tune another coefficient. Keep workingV43/README.
Next compare a larger reviewed corpus under a longer matched stage, initializing
both arms from completed V60wide4k, with loss off. The completed66934-source4×
corpus is ready; v4's75806 requires ongoing4× preparation. No convergence claim,
protected-final score, original schedule mutation or automatic promotion.

All48saved comparisons, 50,264primary cases/72original comparisons and12control
witnesses independently checked. Complete finite91model/91EMA/89AdamW/RNG,
source/data/step1000-original4000 and41logged control inputs verified.19primary
PNGs/23F32contexts/2RGB16 verified; full102MP34.770s singlepass. Hue inference
reuses4704arrays and adds1176V62; independent35280metric fields/1080group scalars.
CPU32cases/192fields/4nativePNGs.38published PNGs:26actually viewed,12oldwhole
SHA-identical views reused; all common V60 noisy/reference pixels and transforms exact.

The first final-audit wrapper failed before outputs because its CPU cwd was the
frozen model checkout while newer report registries live in the root checkout.
Preserved original failure and source, then a distinct recovery changed only
the two CPU working directories. All completed model panels retained. Recovery
owner1977552/creation1792207249.33 completed successfully and exited. Driver
f5cffb31ea706cef06fd822f0c5394707cea0dc0d323b95c90137c0870b83279.

Report docs/sensor-mean-v62-first1k-review.md; JSON SHA256
bb59963ba04138f5479fe529891a5131d73e8304b56d3a1a29d5c428d4287e35.
