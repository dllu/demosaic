# Verify spatial1000 retention and matched RNG without quality inference

The previous turn made progress: global V90 completed original4000, its retained
state/optimizer/source was independently checked, and the matched spatial V91
worker started. This turn verified the same live controller and spatial worker,
then monitored the unchanged training through its retained1000 boundary.

Controller888626/create1792481153.0 and spatial worker1013677/create1792488408.77
remain live. No owner restart, recipe/source edit, extra GPU work or early
quality-score/prediction review occurred. Recorded spatial input prefixes were
continually compared against the completed global run, rather than relying on
a lock/status file alone. All60 recorded observations through spatial1100 match
the corresponding global source/forward/loss-input fingerprints exactly.

Independent CPU audit of the immutable spatial1000 state:

- Checkpoint SHA256
  `a90222eb1ebfc1c783f7042379b755c4e949c63e67eb52fdfdecec5e591ee447`.
  Global1000 remains
  `cb192a890918e25736776ac09307082a19a8b4a3a4299df4511fcf93d2afe265`.
- Both states report actual1000 with the original4000 schedule. Their model
  configurations differ only in `late_rgb_refinement`: global versus spatial.
- All115 spatial model/115 EMA FP32 tensors are finite. All113 AdamW states
  are finite with nonnegative second moments and step1000. The learned RGB
  output and semantic-modulation tensors are nonzero.
- Optimizer groups remain89/24 parameters at1×/20×, with identical global/
  spatial learning rates:8.868298366769956e-6 / .0001773659673353991.
- Python, CPU and CUDA RNG states match the global checkpoint exactly at1000.
  All56 prescribed first1000 observation fingerprints also match, with a
  preserved immutable prefix. This does not independently replay every
  unlogged observation or assert equal numerical losses between the two heads.
- All47 archived model modules match the active frozen source. Shared archive
  hash remains `f59edf34f3a9516f75353d7cd6b432ce5ceb93bc7048d4684358fb3aef72d34f`.
-113 model and113 EMA tensors differ between the trained arms; their two
  context buffers remain common. Distinct learned states do not establish a
  quality improvement.

Executed audit:
`/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1/audit-spatial1000.py`.
Receipt:
`/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1/spatial1000-integrity-v1/receipt.json`,
SHA256 `03422b8bc30c65ff3fd00b4261d054b4d5c04ef4031ffadcede103d115e0c32c`.
Identical public copy: `docs/results/late-rgb-spatial1000-integrity-v1.json`.
CUDA remained hidden/uninitialized in this checkpoint-only audit; no model was
constructed or run and no routine-validation quality value was accessed.

Spatial training continues to its original4000 endpoint. Full matched quality,
actual native-crop review and any performance/promotion decision remain pending.
The existing ten-stage review and deferred inference-probe/CPU-native queues
still wait for their exact predecessors. No implementation test rerun is needed
for this diary/receipt-only change. SOTA/native superiority and100MP/10s remain
unmet/unproven, and the complete PROMPT.md objective stays active.
