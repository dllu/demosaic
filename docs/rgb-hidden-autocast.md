# First RGB encoder stage follows CNN autocast

`model.rgb_hidden_autocast: true` lets the first hidden encoder stage use the
active CNN autocast dtype while retaining the original FP32 physical head and
final native skip. Physical normalization, conditioning, output projection and
expectation inverse retain their existing precision. Explicit FP32 inference is
unchanged. The default is false, preserving old checkpoints and configurations.
The option requires the pretrained RGB backbone and adds no learned tensors.

The [retained-model profile](full-rgb-inference-profile.md) identified repeated
FP32 residual activations and recasts in this first encoder stage. A process-
local prototype with unchanged V37 EMA weights reduced resident four-tile time
from 179.84 to 165.22 ms (eight alternating blocks of ten forwards after warmup).
Output RMS difference was 3.91e-6 camera RGB, maximum 2.75e-4. This is not proof
of preserved image quality or a full-frame speed claim. The full matched quality
and timing review is pending.

An inference-only export makes the numerical policy explicit:

```bash
source scripts/env.sh
uv run --no-sync python scripts/export_rgb_hidden_autocast.py \
  /mnt/external/demosaic/evaluation/synthetic-packed-v37-v38-1k-full427/weights/weights-2e79285ba72003417eb681cae2bc304106548c8a8d3235dd20a4ea7218ec332a.pt \
  --expected-sha256 2e79285ba72003417eb681cae2bc304106548c8a8d3235dd20a4ea7218ec332a \
  --output /mnt/external/demosaic/runs/full-rgb-hidden-autocast-v42
```

The exporter requires a new directory and an exact parent SHA, archives its
source, selects EMA when available and verifies every learned tensor by a
canonical hash after serialization. It changes only the model's precision
policy, performs zero training updates and emits no optimizer state. This
artifact is for inference, not a training resume. The receipt records parent
config/step/hash, tensor hash, exported hash and code identities.

V42 export SHA256 is
`efb90a929cab017d57398016139013a21cd5470f08736a340448ebb9dd494d55`;
its learned-tensor SHA256 matches V37 EMA:
`6502923340722cba257dec52aa55d20bbd0cd91e6a5185dd41fc89e4b3795e14`.
The export receipt is in the same external run directory.

All 329 tests pass (28.09 s). New checks cover encoder/tail dtypes, identical
explicit FP32 behavior, unchanged state-dict keys, zero-noise native ADC ramps
for every CFA under BF16 and odd dimensions, and serialized policy roundtrip.
The original full/packed compatibility tests also pass. Quality review still
requires known/unseen real, full 427-photo/procedural and full 102 MP GFX results
with native crops. The production default remains unchanged during review.
