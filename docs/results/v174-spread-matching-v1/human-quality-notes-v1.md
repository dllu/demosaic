V174 preserves wide sample positions, but does not recover more fine detail than
V172. EMA quiet-field total RMS improves **0.12–0.17% versus V172**, with 24/32
inputs improving; spatial RMS improves **0.04–0.08%** on 29/32 and DC color error
improves **0.36–0.43%**. These are small measured gains, with no clear visual
cleanup in the native crops. Mesh response slips **0.25% to 3.868% of constructed
GT amplitude**, with 208/256 responses lower. Natural fine-band response slips
0.016–0.023%, with 124/128 lower. Present/absent mesh RMS changes only
−0.0002/−0.0082%. Full-flat means change **+0.008/−0.072%** at ISO6400/12800;
coarse-flat means worsen **0.020/0.004%**, with 33/48 individual inputs worse.
Raw quiet total RMS instead worsens 0.12–0.19% versus V172. The seven-method
tables below retain both endpoints and the earlier quiet/flat alternatives.

The six observed EMA contexts retain a coarsest-block 90th-percentile sample
distance of about **90.7 native pixels**, versus about 12.04 for V172. Middle
blocks reach about 45.3 and fine blocks 22.6–23.0. Wider positions alone did not
produce a useful detail gain in this matched 900-update schedule. The bias change
also changes the tanh derivative and optimization conditioning, so this single
seed does not isolate geometric reach as the sole cause. Sample positions do
not measure whether distant content supplies the final RGB correction.

All 60 figures were inspected at original detail. Synthetic seed2302 remains
nearly blank at ordinary exposure and mottled at 40×; seed2309 retains mostly
one wire family while missing crossings. Both fine green cab windows and both
noise priors remain close to V172, with smeared strands and incomplete crossings.
The main sky has no obvious new texture at ordinary exposure, but amplified
quiet and flat crops retain broad colored patches. Building, foliage and bird/
branch/insect controls remain softened. ADC controls keep V169 exactly. Real
ISO100 and independently demosaiced/JPEG references differ in aperture, depth of
field, shutter, motion and processing; they are qualitative references, not GT.

Keep **V172 as the balanced matching baseline for detail work**. V173 remains a
stronger quiet/spatial-error option, V171 a stronger standalone-flat option,
V161 the stronger learned mesh prototype and V120 Small the general choice.
V174 records a small quiet-color gain rather than a combined quality advance.
The [native-pixel viewer](images/v174-spread-matching-v1/native-viewer.html)
opens with V173 EMA versus V174 EMA; select V172 EMA for the main matched
comparison. Click the flip tile or press F. Its
[browser pixel verification](results/v174-native-viewer-verification-v1.json)
checks every displayed crop against the PNG pixels.

A separate posthoc [V175 shortcut diagnostic](results/v175-local-shortcut-diagnostic-v1.json)
tests six selected V174 EMA inputs by removing the whole matching path at its
last fusion. The remaining head-to-tail path is evaluated directly, using six
head and six tail CUDA convolution calls, with no sampler, full matching,
frozen-component or parent/DINO forwards. Its difference from the full added
correction has 18–84% of that correction's RMS. The complete added correction is
only 0.20–0.22 DN16 RMS on these inputs. This rejects a complete bypass on the
tested inputs; it neither isolates distant samples nor explains the remaining
detail loss. Six saved local corrections and their FP32 compositions are
independently checked. Case selection is disclosed, including the absent case
chosen for available saved arrays. This is a functional contribution probe,
not a trained V175 model or a new 822-case quality comparison. Its calls are
separate from V174's matching-work counts below. Further work needs to test how
matching learns useful content and correction amplitude while retaining flat
controls; simply widening positions has not solved the problem.
