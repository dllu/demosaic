# Pass actual normalization CUDA preflight and start matched V68/V69

The previous turn completed the actual original20k review and all58 native
views, preserving an explicit no-promotion decision. This turn moves the prepared
normalization augmentation into genuine production-size CUDA checks and a
matched training experiment. The full PROMPT quality/speed goal remains unmet.

Chose V63 original20k EMA as a common initializer: it stays near V64's photo mean
and has better checked bright-color bias/RMSE. Parent SHA256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
V68 control versus V69 augmentation share fresh AdamW/EMA, seed50, LR3e−6,
warmup100, B16/native256/BF16, workers4+2+2, original40170 Commons/native128/
paired32 data and a new planned4000 horizon. Only training normalization policy,
run and notes differ. Original20k optimizer/checkpoints/reports are preserved.

Added and actually executed `scripts/preflight_normalization_cuda.py`:

- Eighteen discarded updates:6 control,6 augmented and3+3 resumed augmented.
  All three data domains occur, with mixed masks per16-image batch.
- Four-CFA CUDA transformed-feature fixture equals CPU oracle(max0 against
  fixed3e−6 bounds); the zero-mask path preserves default output bits and
  RAW/canvas/CUDA RNG.
- Exact pre-fetch parent-EMA/fresh-optimizer initialization and exact resumed
  model/optimizer/Python/Torch/CUDA RNG restoration; exact pre-update EMA.
- All18 updates have89 finite trainable gradients. Final states91/91/89 are
  finite, all89 model/EMA parameter tensors change, and context mean/std stay exact.
- Actual frozen DINO stays gradient-free/hash-identical at
  `370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
- All six input hashes match across arms/resume. Ordinary FP16 EMA loading
  matches manual restoration on both fixed photos for both augmented states.
- Peak CUDA allocation7.212962304GB. These are not quality/throughput results.

An independent CPU-only saved-artifact audit verifies source bundles, inputs,
helper archives, states, independently reconstructed SHAKE masks and saved RNG.
Its first attempt incorrectly included the separately hashed training manifest
in the source-bundle digest; checking the documented payload definition and
verifying that manifest under its own data hash resolves this without a tolerance
change. Actual full/resumed model/EMA maxima are2.3841858e−7/1.6391277e−7, so
CUDA optimization is not called bitwise deterministic. The10 existing
normalization unit tests and Ruff pass.

Artifacts:

- `/mnt/external/demosaic/benchmarks/normalization-augmentation-CUDA-v1/`.
- GPU producer receipt SHA256
  `57b25b9e44e38a619977e3ed45ca323b1e4ecd6fbe84737b1d08a736c8f39dbe`.
- GPU plan SHA256
  `737bb6b4e632d11aa636d24ef65ee8edcf8f125552abb886461a6a5d49c2820e`.
- New producer source bundle remains
  `db5fb3ba42827e9db043dbc85f069bb1e5568cdafa872f7340d872852bc6a771`.

Prepared an isolated157-guard package/controller. Before launch, corrected its
parent-config comparison to default-resolved ModelConfig because the older V63
checkpoint lacks three later disabled RAW-kernel defaults. The prepared-plan
revision records the old unexecuted hashes. No live/archive training state or
recipe changed. All final guards/inputs and semantic model compatibility pass.

The actual serial training controller is PID497608/creation1792256805.99,
launched17:06:46UTC. V68 child497625/1792256808.06 is live; at17:09:47UTC it
has reached225 updates. Its first input/domain/LR match the discarded fixture
exactly. Loss/gradient arithmetic is not called bitwise deterministic. After
V68 closes/audits1000, V69 runs to1000; neither automatically continues past
this first review gate. The full planned horizon remains4000 in both arms.

Operational state:

- Status: `/mnt/external/demosaic/runs/normalization-v68-v69-first1k-workflow-v1.json`.
- Frozen plan/controller/package/logs:
  `/mnt/external/demosaic/benchmarks/normalization-v68-v69-first1k-workflow-v1/`.
- Final launch plan SHA256
  `a2ab0b292cb34c51f3803a4abf2ada104b6529c5f172d7d2e32363bdb0a44b7d`.
- Public launch/preflight receipt:
  `docs/results/normalization-augmentation-CUDA-and-launch.json`, SHA256
  `7c84add6f5b524b98b0e7003833b76c61e8fde9c805b296a6272c01f4785a7f0`.

No quality evaluation is queued at this launch capture. Next prepare the actual
first1k review while the same trainer runs: fixed427 plus frozen418/416 source
sensitivities, parent/matched-arm comparisons, paired/analytic/hue/native/GFX and
full RGB16 checks. Only the exact training owner's successful terminal state
and actual exit should release GPU evaluation. Warm RAW-cache links exist in
the isolated work directory; original photos remain read-only. Do not rerun
the closed20k workflows, restart the live trainer, substitute future data or
infer quality from the discarded fixture. V43 remains the working reference.
