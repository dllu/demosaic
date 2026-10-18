# First mixed16 quarter archive passes state and portable EMA-load checks

Previous goal turn made progress by promoting and validating the saved-trace
reader. This turn revalidated the exact live training controller/child and
followed that same no-DINO child through the first4k save. Waiting observation
timeouts did not trigger a restart. Training advanced from3725/59600 to4000/
64000 updates/examples and remains active. Quality/profile owners still wait.

Observed the producer's immutable step4000 archive receipt, then ran a
low-priority, two-thread CPU state audit while the trainer continued. Checkpoint
SHA`55d4a093df916f4146fdd4b1d682b020cda0a9b2af3dfe25e4ef15c969020872`.
All852 model/EMA tensors and Adam states are finite; Adam counters all4000,
data_step16000 and example_draws64000. The original40000-update horizon,
IEEE FP32/gain32 recipe/source bundle remain intact. Actual Adam LR is the
original schedule's`0.00019653544138946785`. CPU/Python/CUDA RNG state is present.

Portable CPU checkpoint loading matches all852 EMA tensor values exactly.
All852 current and852 EMA tensors differ from2k. This is state-change and
serialization evidence, not a learning-quality result or executed4k optimizer
restart. No forward or held-out/GFX inference ran. All163 logged macro rows
through4k have original LR/example counts, including163 older source/noise
overlaps. All22 inputs/56 frozen guards and the preserved2k archive remain
unchanged. Exact trainer/controller identities were live before and after;
CUDA stayed uninitialized in the auditor.

Private audit and result are in
`/mnt/external/demosaic/benchmarks/mixed16-quarter-no-dino4k-state-CPU-v1`.
Observed result SHA
`190cbc3f78d49a6e0891f081f0fdb2741e1479527c716567b3195b82799892dd`.
Public registry binds that result, executed source, actual archive/parent,
producer receipt and frozen state-validator/190-guard plan. Documentation
records this intermediate result separately from the pending10k quality gate.
No policy, source admission, promotion, protected-final scoring or extra GPU
job. SOTA, decisive real-photo superiority and100MP/10s remain unmet/unproven;
the broad goal stays active.
