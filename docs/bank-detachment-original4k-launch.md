# Fresh bank-gradient quality study started

V82 connected and V83 detached are running serially under the
[fixed experiment](directional-bank-detachment-v82-v83.md). The connected arm
has completed its first25 updates; the detached arm follows its original4000
boundary. **There is no quality result or model promotion at this milestone.**
[Frozen source, preflight bindings, runtime configuration and verified launch snapshot](results/bank-detachment-original4k-launch-v1.json).

Both arms freshly initialize genuine V63 original20k EMA and use identical
bank architecture, data, seed51, strict B16/native256/BF16 execution, original
4000-step cosine horizon, warmup100 and LR1e-5/branch20x. Only the bank descriptor
gradient policy changes. Cleaned84,867 Commons/native128/paired32 and
4×→geometry/PSF→area2 remain fixed; unused domains stay lazy. The private150
extension remains inactive. Standing GFX and siblings remain excluded.

The exact new controller passed its
[two-arm CPU engineering preflight](results/bank-detachment-controller-cpu-v1.json),
including its final state/source/input/RNG audit. Prior
[genuine-parent CUDA checks](directional-bank-gradient-routing.md) cover six
discarded B16/native256/BF16 updates per setting. Production freezes247 files
from commit`f8c29e8` and runs one arm at a time with the declared resource bounds.

At the recorded launch check, the controller and connected worker are live with
verified PID creation times. All17 first16/step25 input and legacy-target hashes
match the earlier V81 connected reference. The first two logged training rows
also match exactly apart from timing/allocation. This is early reproducibility
evidence, not proof that complete trajectories or final quality are identical.

After both original budgets finish and their exact owners exit, the fixed full
photo/camera/analytic/color/native review will evaluate both final EMAs freshly.
That review includes at least two100% exact-GT crop triplets per checkpoint and
cached GFX sky/building/foliage/fence/lights with independent ISO100-reference
labels. Failed gates keep the study closed without automatic extension.
V43 remains the working reference and README pixels remain unchanged.

Current state is in
`.cache/experiments/bank-detachment-v82-v83-original4k-v1/status.json` and its
arm logs. The published launch receipt is a dated snapshot; process identity
and current metrics must be checked before acting on later state.
