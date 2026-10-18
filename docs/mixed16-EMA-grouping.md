# Grouped EMA: CPU consistency check

One grouped EMA call reproduces the frozen production scalar loop exactly on
the actual no-DINO8k and DINO2k restoration states. This is a CPU arithmetic
check; GPU equivalence and a training-speed benefit remain unmeasured. Production
training and all queued jobs retain their frozen code.

[Complete source/checkpoint hashes, protocol, operator counts and independent replay](results/mixed16-EMA-foreach-CPU-v2.json).

The current EMA loop calls `lerp_` separately for each restoration-state tensor:
852 for no-DINO and 865 for DINO. The latter includes the two preprocessing
buffers alongside its 863 optimizer states. The prototype aligns tensors by name
and calls `torch._foreach_lerp_` once on the actual same-device FP32 state. It
does not instantiate or execute a network, change precision, or update an
optimizer.

Both checkpoints are tested at eight original schedule positions:
1/12/13/2000/2001/8000/10000/40000. Later positions share the capped decay.
Each case starts from the saved EMA, holds the saved model values fixed, and
makes five consecutive updates. These are arithmetic fixtures, not a replay of
the historical training trajectory. All 16 cases / 80 updates / 68,680 individual
tensor updates match byte for byte, with identical strides. Checkpoint bytes,
original input values and CPU RNG stay unchanged; CUDA remains uninitialized.

The independent replay uses out-of-place scalar `torch.lerp`, compares NumPy
bytes for every tensor after each update, and reproduces every saved final
state hash. It reverses EMA dictionary insertion order to check alignment by
name. Both methods still use Torch's lerp implementation; this is not an
independent kernel implementation.

CPU profiling observes one `_foreach_lerp_` call with 852/865 nested `lerp_`
calls. Grouping reduces the top-level calls in Python but retains per-tensor CPU
arithmetic. These counts cannot establish a GPU kernel reduction or a whole-step
speedup. A future bounded CUDA comparison must preserve exact state values and
measure actual timings after the current owned queue exits. Whole-step training
measurements remain necessary before adoption; the already queued inference
profile does not measure EMA work.

The first attempt stopped before DINO arithmetic because the probe incorrectly
expected 863 model/EMA tensors. Its source, plan and failure receipt are retained.
The corrected attempt includes all 865 tensors and keeps the strict byte-equality
gate. Both probe and independent replay pass Ruff. No held-out image, protected
scene, training recipe, model checkpoint or production source changed.
