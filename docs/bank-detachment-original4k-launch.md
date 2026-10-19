# Bank-gradient study: original budgets complete, quality review running

V82 connected completed its original4,000 updates and exited successfully.
V83 detached later stopped at the system-memory guard and saved step2,999.
A [separately frozen recovery](bank-detachment-memory-recovery.md) restored that
checkpoint and completed the original4,000-update boundary under the same
[fixed experiment](directional-bank-detachment-v82-v83.md).
The [independent completion audit](results/bank-detachment-recovered4000-completion-v1.json)
passes; the fresh quality review has started.
**Quality conclusions and model selection remain pending.** The following launch and
connected-completion observations are historical snapshots.
[Completed connected boundary and verified detached handoff](results/bank-detachment-connected4000-reproduction-v1.json).

A read-only CPU audit checks the completed connected checkpoint: all105 model/
105 EMA tensors and103 AdamW states are finite. Model, EMA, optimizer, Python/
CPU/CUDA RNG and best-monitor state exactly reproduce the prior connected V81
at the same seed and inputs. All176 sampled inputs/legacy targets and161
training rows match apart from timing/allocation. Checkpoint metadata/source
identities differ. This is deterministic reproduction, without independent
training-seed evidence or new quality scores. Detached's first19 sampled full/
legacy/input observations through step75 match connected; its full4k budget
and fresh ten-stage quality/native/manual review are still required.

[Original frozen-source, runtime-configuration and launch snapshot](results/bank-detachment-original4k-launch-v1.json).

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

The original controller's failed status and logs remain at
`.cache/experiments/bank-detachment-v82-v83-original4k-v1/`.
Current recovery state is in
`.cache/experiments/bank-detachment-v82-v83-memory-recovery-v1/status.json`.
The published receipts are dated snapshots; process identity and current metrics
must be checked before acting on later state.
