# Full eight-view quality comparison queued

Recorded: 2026-10-24T00:11:38-07:00 (America/Los_Angeles).

Extended the public photo, prepared-camera, weak-texture and analytic-color
evaluators to accept the existing optional eight-view policy. Own checkpoint
labels and provenance record it; references retain their single-view operators.
Color reuse now requires matching inference policy, preventing unchanged weight
hashes from making single-view arrays eligible as eight-view results. The
`quality` CLI exposes the same flag as inference/export.

Thirty-seven targeted tests pass. The actual V104 CPU engineering preflight
completes 24 model/encoder forwards: two photo observations and one prepared
camera crop. All streamed means equal independent NumPy64 reconstruction
exactly; model weights remain unchanged and CUDA stays uninitialized. These
small fixture scores are not new quality results.

Queued the complete frozen comparison: 12,404 photo/procedural observations,
72 known-camera crops, 90 unseen-camera crops, 448 weak/neutral observations
and 1,176 analytic colors. Its 14,190 averaged observations require 113,520
per-image view evaluations. Every mean remains available for independent
scoring/native review; clean photo batches, context metadata and input/view
fingerprints support replay without rerunning the network.

Controller 4127938, creation time 1792825828.32, waits for the exact existing
eight-view full-GFX owner 3963376 to complete successfully. That export already
waits behind the original matched V111/V112 workflow. The controller checks
successful dependency receipts, memory and disk reserves before using CUDA.
Full metrics, native crops and full-frame review remain pending. V104 remains
the current selector; V112 continues its original training.

The executed CPU source and plan remain unchanged. Worker v2 compares CPU
copies in the weight-identity assertion for CUDA, and adds cached context
metadata; neural operators are unchanged. Never-launched queue v1 accidentally
resolved the virtual-environment interpreter symlink; v2 retains its absolute
`.venv/bin/python` path. Sources and plans for both drafts remain preserved.

All twelve original workflow plans and their input/source guards still pass.
The five public operators' old bytes are archived and match Git commit
67f39b3; historical receipts retain their original bytes and paths while the
current public implementation evolves.

Fetched `feat/linear-dng-export`: latest 4381fc2 is already a main ancestor,
so hot-pixel handling and linear DNG support require no further merge.

[Current report](../docs/dihedral-quality.md) ·
[Queue/CPU/source/launch evidence](../docs/results/v104-dihedral8-full-quality-queued-v1.json) ·
[Historical public-source resolution](../docs/results/source-preservation-67f39b3-v1.json).

