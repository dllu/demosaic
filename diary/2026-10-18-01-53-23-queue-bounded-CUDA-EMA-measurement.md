# Queue a bounded CUDA EMA measurement after the existing profiler

Previous goal turn made progress: actual CPU EMA byte-equivalence study and
independent replay, pushed3282f85. Revalidated the same live training, quality
and inference-profile owners. The no-DINO arm advanced from8,825/141,200 to
9,675/154,800 updates/examples during this work, about1.09s/update. Both10k
endpoints, complete quality review and native visual decisions remain pending.

Added benchmark_ema_updates.py and queue_ema_measurement.py, with20 new focused
tests. No production model/trainer code changed. Worker extracts only the
original own hash-checked EMA function, operates on cloned actual FP32 state,
and checks strict byte-equivalence/strides at eight original decay positions,
five updates each. Both queue and worker refuse CUDA until the exact prior
inference-profile owner/child exit successfully. The queue then reuses the
frozen completed-training validator on CPU. Future targets are actual10k states.

Only passing arms time three warmups/ten balanced shuffled samples per method
and record two genuine CUDA traces. A mismatch is retained as a rejection with
no timings. Source/initial-EMA values, checkpoint bytes and all RNG remain
unchanged.300s own-child limit,32GiB RAM/500GiB disk reserves, no restart or
adoption. This measures isolated updates on prebuilt named states, excluding
real model state_dict traversal and all forward/backward/optimizer/data work.
Whole-step timing is still required before any training-speed adoption.

Two genuine CPU preflights use the actual no-DINO8k and DINO2k archives with
CUDA hidden. All16 cases/32 final value hashes match the preceding independent
replay. Four CPU traces contain no CUDA activities; post-timing/tracing states
remain equal and sources/RNG unchanged. Actual CUDA request rejected before
nonexistent input paths are read/output creation; CUDA remains uninitialized.
CPU audit SHA5c2f6503b9aba23c0ca6ed23ebeeda68da7781434e77c86899b81172b92ae717.
Private CPU evidence: benchmarks/mixed16-EMA-benchmark-CPU-v1 under/mnt/external/demosaic.
Forty new/existing focused tests pass in1.96s; Ruff and whitespace pass.

Frozen plan SHA1610f94c3ce380a1064e450c26af31196025a09f87b389e707cf7d489937208f.
Eleven inputs/five guards. New waiting owner2881904/1792313473.11 is confirmed
live and child-free behind2714232/1792306477.92; no GPU EMA work has run.
Live status:/mnt/external/demosaic/runs/mixed16-EMA-after-profile-v1.json.
Both future outputs are mixed16-quarter-EMA-CUDA-{no-dino,dino}-v1 under benchmarks.
All387 unique input/source checks across four workflows pass unchanged.
Free SSD530.57GiB; downloader stays stopped. Published queue registry and method
note. No new training variant, data admission, quality result or production
promotion. PROMPT.md's quality superiority and100MP/10s remain unmet/unproven.
