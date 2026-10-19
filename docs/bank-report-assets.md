# Native crop assets for the final bank-context report

The final crop packager is prepared and queued after the exact evaluation,
CPU closure and working-reference owners exit. It refuses the currently live
review before creating output. It produces a private crop section and metadata
index; actual inspection and the complete performance report remain required.
[Preflight, archived source and live follower](results/bank-report-assets-preparation-v1.json).

For each final checkpoint it requires two exact synthetic-GT triplets and all
four standing GFX regions: sky, building, foliage and chain-link fence. It checks
source/ROI/noise/display agreement and identical noisy/reference pixels across
the two models. It retains complete checkpoint hashes, CFA, white balance,
matrix, source attribution, sensor/cache coordinates and reference descriptions.
GFX crops retain independent ISO100 labels and aperture/motion caveats.

All original PNG files are copied byte-for-byte. Every displayed cell in all
eight final comparison boards is checked against the original native160px source
slice and its pixel hash. No image interpolation, RAW decoding, new inference,
quality decision or README replacement occurs. RGB8 previews remain separate
from the unquantized predictions used for metrics.

The complete archived V78/V79 fixture passes: 81 source triplets and125 board
cells verified, with12 selected PNG triplets copied unchanged. Each of the two
large checkpoints is hashed once, and validated source slices are reused for
cell checks. The archived executed source and input/reference bindings remain
in the package. This historical integration check is not V80/V81 evidence.

The actual follower uses a pinned script and the frozen review environment.
Its eventual output is
`.cache/experiments/directional-bank-v80-v81-original4k-review-v1/work/outputs/report-assets-v1/`:

- `crops.md`: a crop section with source attribution, checkpoint hashes, ROI,
  conditioning and exposure, ready to incorporate after actual inspection.
- `index.json`: complete native metadata and checksums, explicitly marked as
  awaiting manual review with no quality decision.
- `images/`: required individual triplets and all-method comparison boards.

Numerical results, adverse groups, uncertainty limits and actual visual findings
must still be written and reviewed before publishing the performance report.
Neither this package nor the queued criteria checker can establish model
superiority, approve a default change or satisfy the remaining SOTA/speed goals.

Meanwhile the control's retained2k boundary passes read-only checks:99 model/
99 EMA/97 AdamW states are finite, all89 common trainable tensors changed,
the frozen source matches, and96 sampled observations match the original input
stream exactly. The original4k schedules continue; no interim quality decision
or extra model inference is made.
