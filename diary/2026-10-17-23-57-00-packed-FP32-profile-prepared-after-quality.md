# Prepare actual FP32 GPU attribution behind the running quality workflow

Previous goal turn made concrete progress: isolated continuation and complete
quality queue were launched, guarded and committed. Revalidated exact training
controller2645898/1792305192.32, no-DINO child2645905/1792305192.6 and
quality controller2667688/1792305841.61 as live. The no-DINO arm progressed
from2700 to3100 updates /49600 examples during this turn, around1.10s/update.
Training remains unchanged. The broad quality/speed objective is still unmet.

The earlier CPU operator census cannot identify an actual GPU bottleneck.
Added a bounded current packed-model profiler with the review's IEEE FP32
policy, rather than reusing old FP16 timing. Native512/B4/channels-last fixed
GFX inputs, three warmups, five unhooked samples, five hooked samples and one
operator trace. Thirteen RAW ranges, plus DINO context/backbone when present.
Inclusive ranges overlap; samples exclude transfers, tiling/blending and I/O.
No quality score, speedup, algorithm/precision change or promotion follows.

Extracted the existing observational hook context into a shared helper while
preserving its original RAW-kernel wrapper and range names. Current2k V72/V73
CPU/native256/B1/two-thread preflights pass: unhooked/hooked/traced arrays
bitwise equal, model/full DINO state and RNG unchanged,13/15 sampling ranges
twice and traced once, no initialized CUDA or device events. Profiler setup
logs the unavailable GPU probe under CUDA-hidden CPU execution; these are CPU
results and no device timing is claimed.

Independent audit builds packed/variance/CFA/WB/matrix inputs directly from
the frozen NPZ, checks the shot/read variance law exactly and reruns one
unhooked forward per model. All393216 F32 scalars match,28 actual trace ranges
and all source archives verify. Future frozen model sources match both CPU
executions. Audit SHA
`8786f3b672cc3a7686c323d5a42c0f74ee789ff559a6523e54cfde4785f42517`.
Twenty focused tests pass in1.95s, including hook cleanup on exceptions,
canonical tensor hashing, unfinished/failed predecessor rejection, terminal
text with live owner rejection and PID-creation mismatch. Ruff passes.

Frozen profile plan SHA
`16b7cd94dfafecff170a823103c98f8dbed6b745df0824e33b5378ef18f195aa`,
five inputs/52 source guards. Queue controller2714232/1792306477.92 is
observed live, child-free, waiting for exact quality owner2667688. It requires
the complete new quarter terminal, actual controller/final-child exit, all
report hashes and the frozen independent10k training-boundary validator before
any GPU child. Children run serially with32GiB RAM/500GiB disk floors and a
300s timeout applying only to that owned child. No automatic restart.

Public queue registry SHA
`9d674e8f9f18c2a610e78bae596ac45b808e06fe6a24fdd767cb2d7813f4ba45`.
Profile outputs and GPU attribution remain pending, as do full quality/native
inspection and any promotion. No extra compilation experiment is launched;
read actual GPU costs first. Training, protected-final scenes and stopped
Commons downloader remain unchanged. Goal stays active.
