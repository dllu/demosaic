# Check shared-profile physics batching while the fixed quality trial runs

The original4000 V90/V91 trial and all four queued quality/closure/reference/
native-package owners remain live with their exact PID/creation identities.
The latest inspected global-arm record is step1775 with87 actual input/forward/
loss observations matching their frozen expectations. No quality scores were
read, intermediate predictions made, owners restarted or frozen source edited.

The user's three data-path requests are already implemented and measured:
4× binning → geometry/PSF → area2; selected-only domain loading; and B16 retained
from the matched current-pipeline sweep. Existing speed studies already reject
dense width folding on operation cost and TF32x3 on actual CUDA latency; the
older hidden-autocast result also covers a different precision policy. I did
not repeat those studies or run a competing GPU job.

The current stabilized RGB forward still loops over per-tile GAT, MHC and
inverse operations when the caller supplies one common scalar noise prior.
Added an isolated CPU prototype that generates exactly two guarded changes to
the actual forward AST, without editing production. Mixed and equal-vector
profile inputs retain the original AST branches. All47 model modules, original
and candidate forward sources and the exact executed driver are archived.

Executed `/mnt/external/demosaic/experiments/uniform-physics-CPU-v1/`:

- All48 component cases/192 fields/378,048 values match bytes and strides.
  Include five shared noise families, B1/B4, both layouts, odd/even extents,
  negative inputs, all Bayer patterns and two multi-profile fallback cases.
- All184,320 actual V63 original20k EMA outputs match bytes across three
  conditioning cases on four cached native64×80 GFX subcontexts. Model/DINO,
  parameter identities and RNG remain unchanged; CUDA stays uninitialized.
- Shared GFX conditioning reduces measured Python MHC calls5→2, GAT forward
  calls8→5 and inverse calls4→1. Four scalar white-anchor calls and the ordinary
  preview remain. These are not kernel counts or a speed measurement.
- Independent NumPy reads verify all six saved full-model arrays, all66 receipt
  references and exact equality with the earlier physics-cleanup GFX baseline.
  Receipt SHA256 `3b61dc055073d08991903fb6fc5fece2145ce015aa76f2bbf725e4f199968e6f`.
- Ruff passes. The AST generation check ran before the model execution. Its
  initial lint findings and stale hardcoded source hash were corrected before
  creating the experiment directory; there was no failed model run or retry.

Documentation: `docs/uniform-physics-batching.md` and the identical public receipt
`docs/results/uniform-physics-CPU-v1.json`. This is implementation engineering,
without a new model, quality report, native-view claim or GPU/full-frame timing.
No README quality reference/default changed and no further GPU job is queued.

Next evaluate this candidate on actual CUDA serving shapes after the exact
training and complete quality owners finish, preserving the strict1/.25DN16
gate. Batch convolution may change GPU numerical behavior and temporary memory.
The fixed V90/V91 quality comparison still needs its complete evaluation and
actual native-cell review; SOTA/native superiority and100MP/10s remain unmet.
