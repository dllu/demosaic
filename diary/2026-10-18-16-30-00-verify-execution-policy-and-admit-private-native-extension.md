# Opt-in deterministic execution and separate private native targets

Added scoped `throughput-v1` / `deterministic-v1` training execution settings,
explicit checkpoint runtime records and resume guards. Throughput remains the
default; legacy checkpoints without the keys remain compatible. Strict CUDA
requires the verified CUBLAS workspace environment before starting Python.
Caller backend settings restore on success, failure and nested invocations.
Tests exposed an initial conflict between PyTorch's legacy and backend precision
APIs; using the backend API throughout fixes it and preserves the archived
CPU control exactly.

The genuine V63/DINO CPU preflight matches all archived four-update model/EMA/
AdamW/RNG/best state and strict 4 versus 2+2 resume state. Two fresh actual CUDA
B16/native256/BF16 processes match all six inputs, losses and final states across
Commons/native/paired updates. All six legacy observation hashes also match
the original V78 inputs. All99/99/97 states and97 gradients are finite, frozen
DINO is unchanged, and strict peak CUDA allocation is7.33GiB. These engineering
updates are discarded; no closed quality study is reopened.

Four fresh serial timing runs use balanced throughput/strict/strict/throughput
order,15 excluded warmup and45 measured updates, original4000 LR horizon and
identical19 Commons/15 native/11 paired measurement counts. Mean rates are
21.58035 versus12.62488 patches/s; strict is41.5% lower throughput at B16.
Both strict60-update final states and logged losses/terms match exactly too.
Full input hashing is restricted to the separate six-update replays, outside
the timed window. No long-run/platform guarantee or default/batch change.
Plans, isolated228-file source and results are linked from
`docs/training-execution.md` and its result registry.

Connected the22 reviewed personal RAWs through a private SHA-pinned admission.
Public code contains only its digest; per-photo receipt/pixels/capture metadata
stay private. Built separate4x/8x150-capture/120-family extensions, preserving
all128 existing rows and embedded public admission exactly. All32 real legacy
crops match the previous frozen loader,44 private cache/crop checks pass, old
cache mtimes stay unchanged, and archived producer sources still match their
original hashes. Quarantine and nine clipping rejects remain excluded.

A genuine-model native-only CPU check uses the22 private sources for four
discarded updates with finite99/99/97 state and97 gradients each step. Targets
remain low-noise phase-bin estimates, not exact noiseless GT. This is data and
execution verification, not a trained data-benefit result. Active recipes retain
native128/106 and the V43 README comparisons. Source originals are untouched;
only cached data are used. Downloader stays off below its512GiB reserve.

Focused policy/training tests:34 passed. Focused native data tests:36 passed,
1 skipped. Final CPU suite:1,120 passed,9 skipped in93.06s. Ruff, formatting and
diff checks pass. All owned GPU replay/timing jobs have exited. SOTA quality,
broad real superiority over RawNIND and100MP/10s remain unmet/unproven.
