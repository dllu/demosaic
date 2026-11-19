# Training weak detail with an independent-exposure teacher

The [parent-feedback replay](paired-feedback-paths.md) found
that a correction from an independent simulated exposure
reduces covariance with the query parent's errors. This study
tests whether that information can supervise a single-frame
head. It also tests the existing quiet-region and detail
composition on weaker textures beside strong edges.

## Weak texture beside a common edge

The validation panel contains 48 photos separate from the
earlier 96-photo paired panel. Each 256×256 native crop uses
the same Bayer layout and camera transform in both scene
conditions. The base contains the source's low-pass image.
The second condition adds a sharp colored step with a varying
angle and subpixel position. The weak detail uses either
0.065 or 0.115 of the same source high-pass residual. Present
and absent targets in the second condition share the strong
step. The exact-flat role has a constant 96×96 core.

Each scene has independent ISO1600 and ISO6400 measurements
with two separate physical draws per role. After camera
conversion, the largest difference between the clean weak
increments in the two scene conditions is `1.49e-7`
in normalized camera RGB. Clean targets are exactly identical
across redraws. The score reproduces the native 1/8 to 1/3
cycles/pixel band and adds separate near-edge and far errors,
absent-detail residuals, and error orthogonal to the exact
increment. The near region covers native pixels within 12
pixels of the step and the far region starts at 24 pixels.

## Matched training

All three heads start from the same paired EMA above frozen
Corpus 100k. Each head sees the Bayer innovation smoothed by
the same fixed window and uses the previous quiet correction
with strength 0.15. All arms receive exact absolute, paired
and flat supervision. The two teacher arms also match the
frozen original paired head's fine correction, with loss
weight 0.35. The same-draw teacher sees the student's physical
capture. The independent teacher sees the other separately
noised observation of the same scene and role. The inference
composition takes a single sensor observation.

The schedule contains 384 updates and 768 additional training
photos, disjoint from the earlier paired, repeat and projected
training schedules. The four Bayer layouts, two ISO families
and two scene conditions each have 48 source examples per
joint cell. Every source has two independent redraws with
present, absent and flat roles. Four qualification updates
verified the initial equivalence of the students, distinct
teacher observations, finite gradients and frozen upstream
weights. Training is active.
[Frozen training and panel receipts](results/weak-edge-distill-v1/qualification.json) ·
[Source and input archive](results/weak-edge-distill-v1/qualification.tar.xz).
