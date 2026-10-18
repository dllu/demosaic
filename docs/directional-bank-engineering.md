# Candidate-bank context: engineering checks and fixed training

The optional bank-context path passes actual CPU/CUDA optimizer checks and a
new matched V80/V81 experiment is running serially. This is engineering evidence;
there is no trained quality result or model promotion yet.
[Receipts, frozen source and launch identity](results/directional-bank-engineering-and-launch-v1.json).
The [fixed experiment](directional-bank-v80-v81.md) records the hypothesis,
original budgets and review criteria before full training.

The new mixing path sees measurement-derived directional averages as well as
the existing local inputs. It reuses all five candidates and adds 24,543
parameters in six tensors. A separate zero output head preserves the parent's
prediction. It never uses targets or known carrier frequencies during inference.
The source and existing-data settings remain separate from the prepared private
corpus addition; these quality arms retain native128 and paired32.

The 32 focused directional tests include FP64 averaging, initial parent/RNG
preservation, nonzero-parent heads, exact common raw gradients, checkpoint
roundtrip, FP32/BF16 paths, signed constant scenes and learning after the zero
head opens. An impulse outside the local5×5 packed window changes the new bank
input at the center; each fixed direction is still averaged only once per
forward. The final CPU suite passes 1,130 tests with 9 skips in111.10s.
Ruff/format and diff checks pass.

The genuine V63/DINO CPU preflight runs four Commons/native/paired updates at
B1/native64/FP32 for control and bank context. The enabled model also runs2+2
interrupted updates with exact model/EMA/AdamW/RNG/best-state equivalence.
Disabling the option reproduces the previous strict CPU checkpoint exactly;
old configurations normalize the missing flag to false. Initial common weights,
all97 unclipped common gradients, selected batches and parent outputs match.
All105 model/105 EMA/103 AdamW states are finite for the bank model; control
retains99/99/97. DINO is unchanged and gradient-free.

The CUDA preflight runs six actual B16/native256/BF16 updates for each arm under
strict execution. All six legacy/input observation hashes match, and the
disabled control reproduces the earlier strict GPU checkpoint exactly. All97
common initial raw gradients match before clipping, while all103 enabled
trainable gradients are finite each step. Additional head gradients participate
in global clipping; clipped common gradients are not required to match.
Whole-case peak CUDA allocation is7.3963/7.6471GiB for control/bank. These short
runs include startup, validation and checks; they are not throughput measures.
All preflight updates are discarded.

The first CPU attempt stopped before the first bank update: its inherited
zero-head assertion mistakenly included the new randomized hidden layers. The
corrected check distinguishes hidden layers from the zero logit head. Its old
source/plan and failure receipt remain available; the complete CPUv2 check passes.

The initial production controller was launched without sibling scripts on its
safe-path import search list. A final-audit helper import would have failed.
Only the exact owned controller/worker groups were stopped after25 logged
control updates, before any quality review or saved boundary checkpoint. The
corrected controller removes that late sibling import and explicitly receives
the frozen worktree's module paths. The isolated v2 attempt has a new232-file
freeze, fresh optimizer/RNG and both original4k budgets. Data, architecture,
criteria and schedule are unchanged by this driver correction.

The active v2 controller verifies the exact genuine parent, initial local branch
and official DINO identity, retains1k/2k/3k checkpoints, and samples176 observation
records per arm. It will verify finite final states, all161 logged domains/LRs,
matched sampled inputs and final RNG before reporting completed training.
The first active control loss matches the earlier strict replay exactly.
Resource caps remain24GiB CUDA,40GiB available RAM at launch and128GiB root/
500GiB external reserves. Each arm has a10,800s limit. Only owned groups may be
terminated; unrelated jobs remain untouched.

No new full-frame export, protected-final score or README model replacement
follows engineering success. The full fixed photo/camera/color/analytic review
and native crop inspection remain outstanding, including at least two small
100% noisy/restored/exact-GT triplets per checkpoint and cached GFX
sky/building/foliage/fence/lights with independent-reference labels.
