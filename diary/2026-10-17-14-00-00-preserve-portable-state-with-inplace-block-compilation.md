# Preserve portable state with internal in-place block compilation

Previous goal turn: **progress**. It completed the no-DINO8000 boundary and
queued the real full comparison with frozen inputs/tools and actual CPU replay
checks. This turn reverified training959314/1792268410.37, DINO
child991672/1792269725.32 and waiting review982831/1792269396.89 by PID and
create-time. DINO continues making finite updates; no observation timeout or
stale status timestamp caused a restart or overlapping owned GPU work.

The earlier small-block compiler experiment improved synthetic forward timing,
but `torch.compile(module)` wrappers add `_orig_mod` names if exported through
state_dict. Added internal `compile_restoration_blocks` using Module.compile
in place instead. It compiles only local blocks, six body groups and decoder,
retains parameter objects/ordinary keys and leaves physical stems/tail and
DINO outside compilation. Evaluation mode is required; same-backend preparation
is idempotent and incompatible backbone/backend changes are rejected. There is
no CLI option, default compute change or active recipe/source change. Actual
training and queued review continue using their separate frozen packages.

Inspected installed PyTorch2.14.1+cu130's implementation directly and checked
the official2.14 Module.compile documentation. The method updates the call
implementation rather than registering a wrapping module. An initial2.9 docs
lookup was corrected to the actual installed version before implementation.
No PyTorch/library/lockfile update occurred.

Forty-one targeted CPU tests passed in10.64s, with two CUDA-only tests skipped.
They cover nonzero heads, four CFAs, odd rectangles, parameter identities and
all keys/tensor bytes, unchanged physical components, idempotence, portable
reload and invalid-use rejection, plus existing restoration/RAW-native tests.
Ruff and whitespace checks passed.

`scripts/preflight_block_compilation_cpu.py` also completed on the actual
no-DINO8000 checkpoint
abd7345c080cb227d77385647c74614c0416d9316ad2f28c81c31cdd1f1697a2,
using both fixed photo observations in CPU FP32 with Dynamo's eager backend.
All852 parameter/state tensors and identities stay exact, with eight compiled
call implementations and no `_orig_mod` prefix. Predictions are bitwise equal.
Portable state reload has ordinary uncompiled modules and exact tensors/output.
Whole-model state SHA remains
2d6fa0034431fdb73b055d4f8f2c08310021100237096c0677b0b75e0115e575.

Public/full receipt
`docs/results/packed-isotropic-inplace-compilation-CPU-v1.json` and
`/mnt/external/demosaic/benchmarks/packed-isotropic-inplace-compilation-CPU-v1/receipt.json`,
SHAfda8270f203d9b5da2d73dc07e37f61d6de443f937ad6889ed2e6ef117dc2e6f.
The receipt binds actual source, operator, checkpoint and observation hashes.
Its operator is archived beside it. No CUDA initialized, Inductor kernel,
new quality score, modified checkpoint or full-frame timing was produced.

This is execution/state compatibility, not proof of GPU accuracy or speed.
The earlier148ms figure belongs to a separate wrapped-module experiment on a
discarded12-update initializer. Do not transfer that number to this helper or
claim a trained quality improvement/100MP<10s. Genuine Inductor GPU precision,
native-crop and full-frame timing checks remain needed before compute-policy
adoption, after the exact active review owner exits.

No protected-final scoring, new training admission, source-photo writes,
model promotion or README crop replacement. The full PROMPT goal remains
unmet/unproven: SOTA, decisive real-photo superiority and10s are outstanding.
Next: finish the actual matched DINO8000 boundary and frozen full review, then
inspect its real numeric/native results before choosing continuation. Preserve
the whole objective rather than treating this helper's tests as completion.
