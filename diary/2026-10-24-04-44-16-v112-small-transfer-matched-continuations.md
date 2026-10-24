# V112 Small transfer and matched quality continuations

Recorded: 2026-10-24T04:44:16-07:00 (America/Los_Angeles).

Completed the Small lateral rebase onto V112. Reused all 80 cached previews,
Small features and sampling positions. All normalized preview hashes and 320
old V104 target arrays replay exactly; one Small feature check is also exact.
No training source reread, augmentation, RAW decode or CUDA occurs in the fit.
The fixed ridge .001 uses 64 training sources; 16 separate training sources
check transfer. Eight lateral tensors change and 83 other V112 EMA tensors,
including all three gates, stay exact. The deepest stage still fails to improve
feature-check RMS (.35823 blind versus .36555 fitted).

The fitted checkpoint SHA256 is
`6b9a863e43ce17594a629440a86388bff93b92b1df33d05c409bd2678cc323e6`.
It records V112's inherited step20000 and zero new joint optimizer updates.
Four-source mean photo PSNR Tiny/Small is 39.74086/39.72745 ADC-only,
40.90266/40.90232 ISO100 prior, and 33.51165/33.51078 ISO12800 prior. Five of
12 cases improve, range −.09146 to +.06374dB. The two adverse camera crops lose
.20265 and .31692dB; no improvement is claimed. Selected yellow/green ADC biases
are 38.34/53.39 DN16, compared with V112's 32.73/50.89. Nine color cases are
checked, not a full color-tail evaluation.

All 60 native board cells were actually viewed: bark/canopy at two conditions,
two dark camera crops, six GFX contexts and three ADC fields. Two noisy /
Small / exact synthetic GT triplets read back exactly to their viewed cells.
Tiny/Small look close, retaining soft foliage/sign detail and dark-camera
blotchiness. GFX3880 ISO100 remains a separate qualitative reference, not GT.
Tiny photo scores/PNGs and retained color/GFX floats were reused; only two
missing Tiny camera controls were computed. Actual counts are 82 Tiny encodes,
32 Small encodes and 33 restoration forwards, including two bit-exact replays
through the actual serialized checkpoint. Independent Torch64 fits/checks and
176 score fields pass; 46 prediction arrays and 12 old Tiny photo score controls
are corroborated. The public fitter reproduces all eight coefficients exactly.

Preserve two pre-execution mistakes. Resolving the virtualenv interpreter symlink
launched system Python, failing at torch import. The first actual worker then
rejected an incorrect dataset-index/manifest-row assumption. Both had zero
neural forwards or optimizer updates. Its source, failure, claim and empty output
remain preserved. The revised source checks sampled training source IDs, with
all 80 membership/normalization checks passing before encoding. No successful
neural work was repeated to fix metadata.

Prepared matched V114 Tiny and V115 fitted Small continuations from V112
history, 20,000 further updates each, seed63, epsilon .0003, identical cleaned
90,864-source zero-PSF/weak-detail/contrast recipe, fresh AdamW/EMA. Each passed
eight actual discarded CPU64/B1/FP32 optimizer updates: 91 initial EMA tensors
exact to its parent, 89 fresh Adam states at step8, finite model/EMA/Adam and
frozen official encoder without gradients. All eight actual batches, domains,
steps and LRs match. All three data domains occur. Source archive SHA is
`cd35f14079462639b0fac6d9b20052b8bba395a396bcaa668383bd6575569f92`.

New controller PID726126, creation1792842066.86, waits for the exact original
GPU audit owner4138085/1792826759.29 and its successful terminal evidence. It
adopts the 16 CPU updates without repeating them. CUDA checks V114/V115 then
production V114/V115 are prospective, with 40,000 total production updates,
24GiB model quota, 48GiB available RAM, 248GiB free external space before each
phase and 240GiB runtime reserve. Earlier workflow limits remain untouched.
At publication the controller has no children and no CUDA/production updates.
Failure stops without automatic retry. Full endpoint photo/camera/analytic,
native triplet and standing GFX comparisons remain required.

Current docs now describe the completed V112 transfer and real limits, and link
the actual queued continuations. V112 remains selected; prior V104 fit, V113
idle supersession, machine receipts and executed sources remain intact.
The user's `feat/linear-dng-export` is already an ancestor of main.

Public evidence: [transfer](../docs/results/small-v112-lateral-alignment-CPU-v1.json)
and [matched CPU/queue boundary](../docs/results/v112-continuations-queued-v1.json).
Private sources and preserved failures:
`.cache/current-quality-20261023-v1/Small-V112-alignment-CPU-v1/`;
CPU plans/results: `V112-continuations-CPU-v1/`; queued controller/worker/plans:
`V112-continuations-training-v1/` under the same cache root.

Validation: all eight new/private executed source files pass Ruff; the real
16-update CPU checks, independent ridge/score arithmetic, serialized reloads,
native pixel readbacks, frozen-source guards, both recipe contracts, local
documentation links and unchanged V112 selector pass. No broad panel or CUDA
check was repeated. At the final check the new queue still has no child.

