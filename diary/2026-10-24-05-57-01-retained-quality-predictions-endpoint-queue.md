# Retain exact quality predictions and queue matched endpoint evaluation

Recorded: 2026-10-24T05:57:01-07:00 (America/Los_Angeles).

Previous turn was progress: completed full-frame eight-view GFX RGB16/native
review, new crop evidence, and current documentation were committed/pushed.
Revalidated original evaluation/audit owners and matched training controller
against actual PID creation times and live states. The original photo and
known-camera panels finished during this turn, followed by unseen/texture and
the color stage. The photo evaluator reports37.04376239dB over427 sources;
the independent full-input/metric audit is still pending, so this is a completed
evaluator result rather than an independently reconstructed full-panel claim.

Added native FP32 prediction retention with exact supervision. The public
PredictionArchive preserves signed/above-white values, shape/dtype and file/value
hashes, shares supervision across models/CFAs, rejects duplicate observations
and mismatched source/input/target coverage, and detects corrupt files. Existing
color-grid arrays are hard-linked, preserving bytes/permissions and avoiding
duplicate prediction writes. Optional photo/camera/texture/color callbacks
receive actual evaluated predictions and target tensors; defaults remain None.
No model math, normalization, loss, data augmentation or inference default changes.

Thirty-eight focused tests pass in4.05s. They cover archive fidelity/corruption,
source/order/input mismatch, policy identity, target sharing, linked predictions,
photo/camera callback metadata/masks and the complete synthetic texture callback
grid with a nonlearned fixture. Callback tests verify no extra model calls.

Replayed two genuine retained adverse camera observations and their actual
Tiny V112 / fitted Small predictions through the new archive. Four predictions
are bit-exact, targets share two files, and independently rebuilt measured-CFA
PSNR has zero discrepancy. This proof imports no Torch, runs no learned model,
decodes no RAW and repeats no prior experiment computation.
Private proof: `.cache/current-quality-20261023-v1/prediction-archive-proof-v1/`.

Queued full endpoint evaluation after the exact V114/V115 training owner
726126/1792842066.86 exits successfully with all four CUDA/training receipts.
New controller856762/1792846321.65 is confirmed live, waiting without children
or CUDA activity. The source-frozen offline collector and all required helpers
import successfully with CUDA uninitialized. Source comparison proves that only
the two evaluator modules differ from existing training source; the new archive
is additional. The photo observation function is AST-identical to the original,
so inputs need not be regenerated twice merely to verify unchanged code.

Future numerical inputs are checked against the original completed eight-view
witnesses, bound only after preceding owners finish; both new models must receive
identical inputs/targets. Only new V114/V115 endpoints run. Existing V112 primary
rows and stronger RawNIND evidence are fixed controls, with no reference neural
reruns. Policies are ordinary single-view FP32.

Per-model calls/observations are: photo3108/12404, known24/72, unseen30/90,
texture112/448, color1176/1176, GFX4/4, highlights2/2, full-GFX130/520 tiles.
Totals are9172 model/encoder calls and29432 image/tile observations across two
models. Native numerical predictions and actual target/mask/WB/matrix tensors
are retained; selected material sources also keep packed/color inputs. Full-frame
runs keep six native unquantized ROI arrays per model before RGB16 output.
No future endpoint quality is claimed complete by this preparation.

Prospective retention/export budget30GiB; free external space248GiB before the
first stage,216GiB for later stages and208GiB runtime reserve. Stage starts
require48GiB available RAM, with24GiB CUDA allocation quota. These start only
after training; previous frozen resource limits are unchanged. Failures retain
partial work/sources/logs and stop without automatic retry. Current model choice
is unpinned; V112 remains selected while trained results are pending.

Public [archive/evaluation guide](../docs/quality-prediction-archive.md) and
[queue/proof/source receipt](../docs/results/v112-prediction-archive-evaluation-queued-v1.json).
Queue sources and state:
`.cache/current-quality-20261023-v1/V112-continuations-evaluation-v1/`.

Later transition: the original full eight-view evaluation and independent audit
finished successfully. Final NumPy64 photographic mean37.04376071dB, +.24291443
over V104, CI[.23542641,.25064056],427/427 source means up. Known/unseen means
54.33282863/53.99411956dB improve all4/5 scene means over V104. Color ADC mean/max
13.90316/420.89677DN16 and ISO12800 mean/max19.17970/119.35809 remain worse than
V112. Weak4/8/16-pixel gains at18% gray/2% contrast/ISO12800 are
.00296746/.09544602/.63945112. Broad RawNIND superiority and fine detail remain
unachieved. Published two exact full-panel native photo triplets and actually
viewed all six cells; faint lines/cloud texture remain smoothed. Machine receipts
are preserved, with separate publication/native-view evidence.

The first V114 CUDA check exposed a missing multiprocessing main guard in the
earlier prepared accounting wrapper. A spawned worker re-entered the script;
the original controller hit its declared check deadline and stopped its child.
The authoritative root receipt records zero prepared batches, model/encoder
forwards and optimizer steps. No first-output archive, metrics or checkpoint
was produced. Its dependent quality controller stopped without CUDA. All old
owners/children exited; no manual process signals were sent. Original sources,
logs, receipts and partial directories remain intact. A preservation snapshot
also records the source/log/status bytes observed during diagnosis.

Created fresh training-v2 output/source roots while keeping the exact original
frozen training code, recipes, data and16 completed CPU updates. The corrected
GPU wrapper has a main guard and proper nonlocal root-training mode accounting.
A genuine Python spawn probe imports it as __mp_main__ without running the
worker or initializing CUDA. Both actual native256/B16/BF16 eight-update checks
then pass:16 prepared batches,16 model/encoder calls and16 optimizer updates,
finite state, matching source archives and all8 Tiny/Small input/domain/LR rows.
V114's fresh original20,000-update production run has started. Small follows.

New training owner867877/1792848017.25; new endpoint-evaluation owner
868302/1792848232.8 waits correctly without children. Both replace only failed
zero-work attempts; no successful neural result or CPU check was repeated to
repair metadata. The earlier queue receipts retain their historical states.
[Guarded-launch/source/failure/CUDA evidence](../docs/results/v112-spawn-guard-training-and-evaluation-v2.json).
Fresh roots: `V112-continuations-training-v2/` and
`V112-continuations-evaluation-v2/` under the same cache parent.

Final verification at 2026-10-24 06:56 PDT: all twelve frozen plan guards
pass, Ruff passes for all nine changed/new Python implementation/test files,
local links in all fourteen changed/new Markdown documents resolve, and git
diff whitespace checks pass. The 38 focused tests already passed; no neural
experiment or test run was repeated for bookkeeping. Original eight-view
owners have exited successfully and both terminal result hashes match.
The current learned checkpoint remains V112 with canonical SHA21c3cca8…;
only recommendation metadata changed. V114's production log has passed step
2225; the exact training owner remains live, and its dependent evaluation
owner waits without children. Hot-pixel/linear DNG branch is already an
ancestor of main. Broad real-camera superiority and fine-detail restoration
remain active goals, with no new trained endpoint quality claimed.
