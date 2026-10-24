# Explicit training execution settings

The trainer now accepts `training_execution: deterministic-v1` for controlled
experiments. Two fresh CUDA processes complete six real mixed-domain optimizer
updates with exactly matching model, EMA, AdamW, Python/CPU/CUDA RNG states,
inputs, and logged losses. The default remains `throughput-v1`.

The implementation checks below used the recorded V63 study setup. Current
[V111/V112 trial](loss-scale-training.md) uses V104 on 90,864 sources. V111
completed20k with [early material/GFX review](v111-early-quality.md); V112 is
training after its verified same-parent handoff. The
[actual launch](results/v104-loss-scale-training-started-v2.json) preserves a corrected
zero-update queue handoff failure. V104 completed 20k from V102 on 90,872 sources;
V102/V103 used V101 and 88,477 sources. Each run retains its actual settings and evidence.

The genuine V63 initializer, official frozen DINOv3 ConvNeXt-tiny, original
4,000-update learning-rate horizon, B16/native256/BF16, channels-last layout,
and that study's Commons 84,867 / native 128 / paired 32 sources remain fixed. The first six
domains are Commons, native, Commons, Commons, native, paired. All 99 model / 99 EMA /
97 optimizer states and all 97 trainable gradients are finite; DINO remains frozen
and unchanged. Peak CUDA allocation is 7.33 GiB. These short updates are discarded
engineering checks, not improved models or image-quality evidence.

The CPU check uses the same genuine model at B1/native64/FP32. Four default
updates reproduce the archived pre-change control exactly, including model,
EMA, optimizer, RNG and best-validation state. Strict four updates match a 2+2
resume exactly and exercise all three domains. Tiny real validation runs on the
original targets; its scores are not quality comparisons.

## Reconstruction loss smoothing

`reconstruction_charbonnier_epsilon` controls the Charbonnier scale for
synthetic Commons/native reconstruction, including linear, rendered, spatial
gradient and auxiliary terms. The default remains **0.001**. Paired RAW keeps
its existing **0.0001** scale; interval and noise-normalized sensor penalties
also retain their separate definitions. The trainer stores the validated value
and refuses to resume with a different one. Missing legacy metadata means the
original default.

The [loss diagnostic and option](loss-smoothing-detail.md#configurable-training-scale)
record 139 passing tests, exact default V102 CPU training replay and exact
nondefault 4+4 resume. All 324 archived full output-gradient tensors also match
the new API. These establish implementation behavior, with no trained quality
gain. A separate eight-update CUDA/native256/B16 preflight also passes with
.0003, exact initialization/encoder identity and finite model/EMA/Adam state.
[CUDA evidence](results/reconstruction-epsilon-CUDA-v1.json).
Existing source-frozen runs and capacity preparations keep their code
and loss settings; a new comparison needs a fresh preparation.

## Explicit frozen backbone identities

The quality recipe operator now records an encoder model name, pinned revision
and measured state SHA256 for the parent and each arm. This allows a declared
Tiny/Small comparison while retaining strict restoration settings. Legacy plans
keep their original shared-hash behavior and original field-by-field checks.
The encoder expectation is checked against the loaded model at training entry,
each quality loader and RGB16 export; an incorrect state hash fails before a
learned prediction.

In a recipe that selects the pinned Small model, record the measured encoder
state hash alongside its model configuration. The common initializer's encoder
has its own expectation:

```yaml
expected_dino_sha256: 691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14
parent_dino_sha256: 370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd
model:
  dino_model: facebook/dinov3-convnext-small-pretrain-lvd1689m
  dino_revision: 421020015aa4266363db803b6049a529999afb1e
```

These fields supplement a complete quality recipe. The SHA identifies the
loaded encoder state; the separately recorded weight-file checksum has a
different role. The default expectation remains the original official Tiny
state for existing recipes. New source-frozen plans include the identity
validator with their operator dependencies, including reports that reuse older
numerical source snapshots.

Actual CPU integration passed two fresh eight-update workers from the same
V102-derived gate-zero initializer file, then a three-model report with 72 score
rows and exact arithmetic. A deliberately wrong Small hash was rejected before
any learned forward. A cached 512 GFX export check produced six RGB16 TIFFs;
all 4,718,592 channel values reopen within .502 DN of their float inputs, with no
RAF decode or CUDA. Fifteen native 160 cells were actually viewed. These are
discarded integration fixtures, not completed quality models or whole 102MP
operation. [Source, tests, model identities and actual receipts](results/mixed-backbone-operator-CPU-v1.json).

The [capacity diagnostic](convnext-small-capacity.md) explains why copying
Tiny's learned fusion into Small is not a trained capacity result. Derived
inference checkpoints also work in texture/GFX reporters when their metadata
has no training-run directory; the original checkpoint filename supplies the
report label. Existing checkpoint hashes and machine receipts retain their bytes.

## Fixed references alongside derived initializers

An initialization transform can change a model before any new training. Keep
the original useful checkpoint as a separate reference. The quality queue now
accepts `--references` with a JSON list binding each reference label, absolute
checkpoint path, full file SHA256, expected step and frozen encoder identity.
The manifest and checkpoint files become frozen plan inputs. Labels and file
hashes must be distinct from the initializer, trained arms and other references.
Actual loading verifies the declared step and encoder before a prediction.

For the prepared capacity recipes, use
[`quality-v102-backbone-reference-checkpoints-v1.json`](../configs/quality-v102-backbone-reference-checkpoints-v1.json)
for original V102, and label the common initializer `V102-zero`. Its inherited
step 20,000 describes the base restoration weights; zeroing the three gates
adds no training updates. After the actual training controller has launched,
prepare the reporting queue with these additional arguments:

```bash
--parent-label V102-zero \
--references configs/quality-v102-backbone-reference-checkpoints-v1.json
```

The fixed references accompany the initializer and completed arms throughout
the quality panels and complete GFX export. New full-frame plans also freeze
their current record validators in a separate operator directory, ahead of an
older queue's helper modules. The queue's numerical source and existing frozen
files retain their bytes. Plans without extra references keep their original
record sets and training-completion checks.

Actual CPU reporting with original V102, its derivative and two earlier
discarded eight-update Tiny/Small fixtures completed 84 case rows. All 72
previous case scores and 18 native panels reproduce exactly. An incorrect
original-reference step is rejected at the loaded-state check with zero learned
forwards. The cached 512-pixel GFX export produced four RGB16 TIFFs; all
3,145,728 channel values reopen within .502 DN, with no RAF decode or CUDA.
All 16 native review cells were viewed; weak umbrella/cloud detail and GFX
foliage remain soft. These are integration checks, with no new training or
quality gain. The 146 targeted tests include fresh-process import precedence
for older queue snapshots. [Actual plans, model identities and receipts](results/fixed-reference-operator-CPU-v1.json).

## Configuration and resume

Add this to a new experiment's YAML:

```yaml
training_execution: deterministic-v1
```

For CUDA, set the verified workspace value before starting Python:

```bash
source scripts/env.sh
CUBLAS_WORKSPACE_CONFIG=:4096:8 uv run --no-sync demosaic train \
  configs/your-experiment.yaml --initialize /path/to/parent.pt
```

Strict mode disables cuDNN benchmarking, enables deterministic cuDNN and
PyTorch algorithms with errors rather than warnings, and requires that workspace
value. Throughput mode enables benchmarking and disables deterministic
enforcement. Both use the explicit backend precision API compatible with the
model's IEEE FP32 guards. Each invocation restores the caller's prior backend
settings on success or failure, including nested invocations.

Checkpoints record the policy and actual runtime settings: PyTorch version,
device type, backend precision values, benchmark/determinism flags and CUDA
workspace value. Resume rejects a changed policy; strict resume also rejects
different recorded runtime values before constructing the model. Old checkpoints
without the keys mean `throughput-v1`. To change policy, initialize a new run
with fresh optimizer/EMA/RNG instead of resuming the old trajectory.

The runtime record is not a complete hardware/driver/environment fingerprint.
Six updates and one CPU restart do not prove long-run or cross-platform
determinism. No closed quality study is rerun or reinterpreted; this does not
identify the cause of a historical process difference. The
[earlier no-update replay](directional-firststep-execution.md) remains a separate
diagnostic.

## Validation and timing

The focused training/execution tests pass 34 cases. The final CPU suite, including
the separate private-loader integration, passes 1,120 tests with 9 skips. Tests cover the
actual local-model optimizer/resume path, legacy checkpoint compatibility,
policy/runtime rejection, invalid CUDA environment refusal before CUDA
initialization, RNG preservation and caller-setting restoration. An initial
test failure exposed mixing PyTorch's legacy and backend precision APIs; the
wrapper now consistently uses backend precision settings.

The real-model replay freezes 228 files in an isolated worktree. Run
`scripts/preflight_training_execution.py prepare OUTPUT`, then its frozen worker
for the three CPU cases and audit before the two CUDA cases and audit. Use the
frozen worktree's `src:scripts` on `PYTHONPATH`; hide CUDA for CPU cases. The
separate `scripts/benchmark_execution_policies.py` compares warmed mixed-domain
training at the same fixed batch size. Policy timing must be assessed separately
from the older batch-size sweeps.

The completed four-process comparison uses balanced throughput/strict/strict/
throughput order. Every fresh run excludes 15 warmup updates and measures 45;
the measurement window contains 19 Commons, 15 native and 11 paired steps.
Observation hashing is disabled in all timing runs. Timing includes selected
data loading, augmentation, degradation, frozen DINO, forward/backward, clipping,
AdamW and EMA. It excludes initialization, warmup, validation, checkpoint writes
and the final state audit. All cases retain the original 4,000-step LR horizon.

| Execution policy | Mean native256 patches/s | Two-run range |
| --- | ---: | ---: |
| Throughput | 21.5803 | 21.4638–21.6969 |
| Strict | 12.6249 | 12.5993–12.6505 |

Strict throughput is **41.5% lower**, or about 1.71 times the time per update in
this fixture. These are two-run ranges on a shared machine, not confidence
intervals or a batch-size optimum. Both strict 60-update checkpoints also have
exact matching model/EMA/optimizer/RNG states and all 60 logged losses and terms.
Complete input hashes are checked separately in the six-update replay, rather
than in this timed window. Neither policy's discarded checkpoint is promoted.
Throughput remains the default; future controlled studies can choose strict
execution explicitly after budgeting for its measured cost.

[Plans, frozen source, CPU/CUDA audits, timing and 60-update state check](results/training-execution-mixed-v1.json).
