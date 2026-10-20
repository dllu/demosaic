# Prepare saved-array and native review behind the deferred GPU probe

The previous goal turn made progress: it committed/pushed the fixed GPU probe,
passing unchanged-weight CPU switching and ownership tests, and queued it
behind the complete V90/V91 quality chain. At entry verified the actual training,
review and GPU-probe controller PIDs/creation times. The global arm was at2200
with104 matching recorded hashes; the probe owner was live and child-free.

Added independent saved-array arithmetic and native rendering without model
inference, plus a CPU-only watcher behind the exact GPU controller/worker.
No active training/evaluation/probe source or recipe was edited. Production
defaults and the V43 README reference remain unchanged.

CPU integration reuses the previously completed actual TF32x3 CUDA outputs,
explicitly labelled as historical fixtures; it does not impersonate a current
uniform-physics GPU result:

- All six full saved pairs/7,077,888 RGB values reproduce the older independent
  numerical audit with FP64 subtraction and scalar fsum. Timing arithmetic
  reproduces the old medians/ratios, without any fresh timing.
- Two photo targets replay from their exact original8×-binned source caches.
  The standing GFX sky/building/foliage/fence source and qualitative ISO100
  reference arrays are checked locally; no original RAF/HDD is accessed.
- Re-rendered24 native160 triplets. All72 actual panels match the historical
  report pixels exactly. Four boards contain48 native cells, deduplicating
  repeated photo noisy/reference rows. All shared source/ROI/noise/WB/matrix/
  exposure settings remain identical across methods. Manual viewing is false.
- Production audit entry rejects the actual still-live GPU/training owners
  before creating any review output. CPU64×80 preflight arrays cannot pass
  the production256/512 output-shape contract.

The first historical integration failed at its final cross-version lookup:
new baseline policy `original` versus historical `IEEE`. All failed v1 source,
logs, arrays/reports and failure-record.json remain preserved. Corrected only
the historical lookup and ran a separate v2 directory; no model forward,
noise draw, actual GPU failure or automatic retry occurred.

Successful receipt:
`/mnt/external/demosaic/experiments/uniform-physics-review-preflight-v2/receipt.json`,
SHA256 `8f6c9464612003cbf9da81b4d5e0ae1cbf8c4ecdb69a7275b56327e598350adc`.
All26 focused tests pass in1.18s; Ruff and formatting pass. Public receipt:
`docs/results/uniform-physics-review-preflight-v2.json`.

Queued CPU review root:
`/mnt/external/demosaic/experiments/uniform-physics-CUDA-review-v1/`.
Owner965128/create1792485817.73, plan SHA256
`e5d4e637e798f7b0714bfad63d56acbe22754bf424d65a6d62ce8c41d0ce69c1`.
All60 source/proof/test/queue bindings verify. Actual waiter is live, child-free,
18.4MiB RSS, without mapped Torch/CUDA libraries or array/native output. Its
exact preceding GPU owner955417/create1792484897.61 is still live and waiting.
Queue verification SHA256
`0550cf90412a885fb68894fa5146ad9346f3113eea8d6c5cdf621ca496c386a6`;
public copy `docs/results/uniform-physics-review-queue-v1.json`.

On completed GPU success: audit all eight output pairs at original1/.25DN16
limits and fixed timing order, then prepare24 triplets/four48-cell boards.
On numerical rejection: audit its failed prefix without timing or a full native
package. In either case, manual review and any integration decision remain
pending; there is no automatic model/default change. CPU launch/runtime RAM
floors32/24GiB, system/external reserves64/500GiB, bounded waits30h/1h and3min
per CPU stage; only exact owned children can be stopped.

At final inspection, global training is at2600 with120 recorded actual
source/forward/loss hashes matching. Training and both waiting controllers
remain live; no quality scores were read and no competing GPU job was started.
The fixed V90/V91 full evaluation/native review, actual batching CUDA result,
SOTA/native superiority and100MP/10s objectives remain incomplete.
