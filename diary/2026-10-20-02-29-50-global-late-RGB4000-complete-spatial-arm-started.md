# Global late RGB original4000 complete; matched spatial training started

The previous turn was progress: the recent WGCAN release and fixed CPU transfer
were checked, with a negative small-pilot result and actual native views. This
turn first verified the exact live training/review/probe owners, then monitored
the original run through its first complete quality-training budget. No new
model intervention, competing GPU work or early quality interpretation occurred.

Global V90 completed all4000 original updates. Worker889750/create1792481225.19
exited successfully, and the original controller888626/create1792481153.0
recorded `control` complete. It then passed its stable resource gate and
started spatial V91 under worker1013677/create1792488408.77. The same original
4000 horizon, source, data, LR and resource bounds remain in effect.

An independent CPU handoff audit checks the actual retained global checkpoint,
without model inference or reading routine-validation/final quality scores:

- Retained4000 SHA256
  `ba40d88149726c48f90d33399cf6ee4666daad470bff82bdfddf994a5e5eb3c4`;
  matches the completed worker's last-state hash exactly.
- Retained1000 SHA256 remains
  `cb192a890918e25736776ac09307082a19a8b4a3a4299df4511fcf93d2afe265`.
- All115 model and115 EMA FP32 tensors are finite; all113 AdamW states are
  finite, have nonnegative second moments and step4000. New RGB output and
  semantic-modulation tensors are nonzero in both model and EMA.
- Optimizer groups contain89/24 parameters with1×/20× multipliers. Final LRs
  are1.0000000000000002e-6 /2.0000000000000005e-5, retaining the original
 4000 schedule and10% floor.
- All47 archived model modules match the actual frozen worker source. Archive
  SHA256 `f59edf34f3a9516f75353d7cd6b432ce5ceb93bc7048d4684358fb3aef72d34f`.
- All176 prescribed actual source/forward/loss-input hashes match. All161
  scheduled training-log source witnesses agree with those observations.
- Spatial first16 observations match global exactly; a preserved immutable
  prefix is stored with the audit. Initial model/DINO and canonicalized first
  gradient fingerprints also match exactly. The later live check through
  spatial75 confirms all19 recorded spatial observations match the corresponding
  global prefix. Numerical training losses after the first step are not asserted
  equal between different heads.

Audit source:
`/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1/audit-global4000-handoff.py`.
Receipt:
`/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1/global4000-handoff-v1/receipt.json`,
SHA256 `89766a4940fa82adea8cc02fc652f7378a1f3adaec0441a2863d68235532b131`.
Identical public copy:
`docs/results/late-rgb-global4000-handoff-v1.json`.

This is trained-state/data integrity evidence, without a new performance report,
prediction, native-view claim, model selection or promotion. Both original4000
endpoints and the fixed full quality/native review are still required. The
existing review/closure/reference/package, physics CUDA probe and CPU-array/native
review queues continue waiting for their exact predecessors; no owner restart
or source/recipe change was needed. SOTA/native superiority and100MP/10s remain
unmet/unproven; the full PROMPT.md goal stays active.
