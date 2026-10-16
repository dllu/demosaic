# Explicit hidden autocast policy ready for matched review

The previous goal turn made progress: V40/V41 completed their full quality
review and native-crop publication, and a retained V37 profile identified the
first encoder's FP32 residual activations/casts. Current state revalidated the
terminal controller, missing process handle and clean pushed commit5e265e4.
No training/evaluation job was restarted. The Commons downloader remains live.

A process-local first-encoder input cast prototype with unchanged V37 EMA
weights reduced resident four-native512-tile time from179.84 to165.22ms across
eight alternating ten-forward blocks. Output RMS distance is3.91e-6 cameraRGB,
max2.75e-4. This is a numeric/speed probe, not a quality result or full-frame
timing. The original FP32 physical head/native skip remains available to the
final projection; only the hidden branch is cast.

Added opt-in `rgb_hidden_autocast` with defaultfalse. It follows current CNN
autocast dtype, preserves explicitFP32 behavior, requires pretrained-RGB and
adds no learned tensors. `scripts/export_rgb_hidden_autocast.py` produces an
inference-only checkpoint after exact parent-SHA validation, archives code and
verifies identical learned tensors after serialization. Existing checkpoints
and model configurations keep their original behavior. The config comparison
already rejects a changed policy during training resume.

V42 export from V37 EMA has checkpoint SHA
`efb90a929cab017d57398016139013a21cd5470f08736a340448ebb9dd494d55`, tensor SHA
`6502923340722cba257dec52aa55d20bbd0cd91e6a5185dd41fc89e4b3795e14`.
No training updates were performed. The receipt/source archive is under
`/mnt/external/demosaic/runs/full-rgb-hidden-autocast-v42/`.

All329 tests passed in28.09s; Ruff passed. New tests verify dtype separation,
FP32 identity, state-dict compatibility, all-CFA native16-bit ramps underBF16
with odd dimensions, and checkpoint policy roundtrip. Source is ready to freeze
for known/unseen real, full427/procedural and full102MP GFX review. Cached
comparators need exact protocol/classical parity; native triplets remain
required. Full-frame timing should alternate original/exported V37 weights
on the same cached input rather than comparing different-day measurements.

No quality/speed promotion yet. Broad RawNIND superiority, current trained
DINO ablation, protected-final scoring and10-second100MP remain unproven.
