# Center the camera-matrix optimization coordinates

The [camera-projection diagnosis](native-low-noise-camera-diagnosis.md) exposed a
large low-noise color bias. [V46's complete review](camera-projection-v46-review.md)
shows why simply deleting the camera inputs is insufficient: photographic and
procedural PSNR improve, but known-camera accuracy falls. This experiment keeps
all camera information and changes its optimization coordinates instead.
**Implementation tests pass; trained quality remains unproven.**

Camera matrices are expressed relative to identity. With matrix weights W,
trainable bias b and fixed parent diagonal reference R, the first projection is:

`head = original_projection(condition) - sum(diagonal_weights - R)`

Equivalently, its matrix contribution is `W (M-I) + b + R I`. At initialization,
R is copied from the parent's three individual diagonal columns, so the
correction is exactly zero. Every common trainable tensor and the original
forward remain unchanged. During training the matrix-weight gradient sees
`M-I`; the bias remains free to learn an unconditional offset. No matrix entry,
WB feature, CFA sample/mask, physical anchor or DINO feature is removed.

This is a hypothesis about conditioning of the optimization. Matrix features
near identity contain a large constant component that can contribute to bias
updates through several correlated weights. Centering separates that component
from camera variation. It does not restrict the projection's representational
capacity, guarantee better optimization or prove the original failure's cause.
Its reference comes from parent weights, not fitted evaluation pixels.

`model.rgb_center_camera_matrix` defaults to false. The default projection uses
its original implementation and state keys. The optional path stores a fixed
64×3 FP32 reference buffer, adding no trainable parameters. Keeping individual
columns avoids different CPU/GPU rounding when copying a pre-summed reference.
The reference persists through checkpoints/EMA and never resets on resume.
Initializing an older parent derives it after strict weight loading; an already
centered checkpoint missing it is rejected. Physical FP32 and hidden-precision
policies remain unchanged. Both full-resolution and packed paths use the same
projection helper.

Six targeted tests cover exact parent forward/trainable tensors for both paths,
zero diagonal gradients at the neutral matrix with sensitivity to matrix
changes retained, fixed-reference preservation after updates, portable loading,
missing-buffer rejection and exact interrupted/resumed optimizer/EMA/RNG state.
The complete CUDA-enabled suite passes **358 tests in 27.81 s**. The
[genuine-weight GPU preflight](results/camera-centering-gpu-preflight-v1.json)
verifies exact initial predictions in FP32/BF16/FP16 for all four CFAs at three
noise priors, with identical common trainable tensors and no added parameters.
A two-update full-state checkpoint resumes to four with its original fixed
reference preserved in model/EMA and exact EMA reloading. These checks are
separate from quality evidence.

## Matched training gate

The [guarded workflow is launched](results/camera-centering-v47-v48-launch.json)
in frozen source7cd1f12; quality results are pending. It trains the two arms
sequentially, checks all logged observations, then runs the complete review.

[V47 control](../configs/dino-camera-control-b16-v47.yaml) and
[V48 centered](../configs/dino-camera-centered-b16-v48.yaml) share immutable V43
first1000 EMA `8ee3e960acdf95d88ba06eab30ac9abbab8bab28b0dc63d79b304a960eb535c5`.
This predates the large procedural regression. Both use fresh AdamW/EMA, seed50,
batch16, base LR3e-5/planned3000 schedule and a first gate after1000 updates.
Common trainable tensors and initial predictions must match exactly. The only
new state is V48's derived fixed reference.

Complete Commons4, reviewed native128, paired training, original8× validation,
25% paired/25% native/50% Commons, pre-reduction geometry/PSF, genuine pinned
frozen DINO and original full-resolution arithmetic stay fixed. Low-rank and
hidden-autocast variants remain off. No new random branch is added; all41 logged
input/target fingerprints must match across arms at the first gate.

Run sequentially in a frozen checkout and review known/unseen paired data,
all427 photographs/16 procedural patterns, full102MP GFX and at least two exact
synthetic-GT native triplets per checkpoint. Preserve accurately labeled AHD and
separate ISO100 references, identical crop/display settings, source/checkpoint/
noise identities and verified RGB16 outputs. Current V43 remains the reference
until the complete new quality review supports a selection.
