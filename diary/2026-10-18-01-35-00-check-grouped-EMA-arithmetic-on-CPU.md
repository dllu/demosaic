# Check grouped EMA arithmetic on CPU while the matched trial advances

Previous goal turn was a verified wait on the exact live trainer. Revalidated
training2645898/1792305192.32 and2645905/1792305192.6, plus queued quality
2667688/1792305841.61 and profile2714232/1792306477.92. The no-DINO arm
advanced through8200/131200 and8250/132000 examples while inspecting code.
No production source, plan, recipe or queued job changed.

The scalar EMA loop issues one Python lerp call per restoration-state tensor.
Prepared a CPU-only consistency diagnostic using the actual no-DINO8k and
DINO2k checkpoint bytes and the AST-extracted hash-checked production EMA
function from the frozen training worker. No model construction, inference,
backward, optimizer update or GPU work. Fixed eight original adaptive/capped
schedule positions and five repeated EMA updates per case, with the saved model
weights held fixed; strict byte-equality/stride preservation required.

The first executed probe incorrectly expected863 DINO model/EMA tensors and
stopped on that inventory assertion before DINO arithmetic. Actual model/EMA
counts are865, with two preprocessing buffers besides863 optimizer states.
Preserved its source/plan and failure receipt in mixed16-EMA-foreach-CPU-v1.
Corrected the expected count and explicitly aligned grouped tensors by name in
v2. No numerical tolerance was relaxed and no failed production training run
occurred. A draft copy command also stopped before writing its source because
its whitespace-specific replacement guard did not match; the v2 source was
prepared correctly before its first execution/plan freeze.

Completed16 cases/80 updates/68680 individual tensor updates: all byte-identical,
zero maximum absolute difference and unchanged strides/source input values/RNG.
CPU operator profiles still show852/865 nested lerp operations inside the
single foreach call. No GPU equivalence, kernel-count or speed claim follows.
CUDA stays uninitialized. Independent out-of-place scalar replay matches every
saved hash and direct NumPy tensor bytes after every update, including reversed
EMA dictionary order. Exact original checkpoint hashes remain unchanged and all
four exact owners remain live. Both scripts pass Ruff.

Private source/plan/result/audit:
`/mnt/external/demosaic/benchmarks/mixed16-EMA-foreach-CPU-v2/`.
Plan SHA230795489e0c3cd620cc616c9589a24899ce3aa572607f04397efc64ef75321d.
Result SHAd9f8befdb7e4d26030ebe0deac6b8ab9f37ff6781938707d6b5470b26940417d.
Replay SHA2832623ab50a3afa663b37104dedbff139ea01aaeb8a2e3521e4b3b6260cef8a.
Published docs/results/mixed16-EMA-foreach-CPU-v2.json and concise method note.
The grouped update is not adopted. A later bounded CUDA numerical/timing check
and actual whole-step timing are required after the current owned queue exits.
The existing future GPU profile measures inference, not EMA. Both10k quality
endpoints, native visual review and PROMPT.md's quality/speed goals remain pending.
