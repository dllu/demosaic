# Review camera crops and fix the watcher startup race

The previous turn made progress on first-photo native inspection and explicit
package/probe queue recovery. This turn verified the exact live full427
worker, then built completed known/unseen camera boards from existing PNGs
using the frozen final assembly functions. Source/ROI/noise/exposure and
independent AHD reference labels remain intact; no inference or resizing.

Both boards were actually viewed at original detail:28 shared160px cells
from20 source triplets, covering V90/V91, fresh V63 and retained V43/RawNIND.
Global/spatial appear very close. Major plate/diagonal edges and the pale
strand survive; smooth regions dominate these selected crops. One chart
view has more uneven RawNIND edge color/texture, without establishing broad
camera superiority. AHD remains an independent auxiliary demosaic, not exact
RGB GT. Public record: `docs/results/late-rgb-early-camera-native-view-v1.json`,
SHA256 `bed134de525215f8eada9c4d92c9c8ee65142ea0ffd31661c31fdd62d1f4459e`.
Final camera-board byte/cell equivalence and the remaining native panels
still need review before counting complete125-cell coverage.

The actual prior CPU-watcher startup failure motivates a guard in
the current repository source. When the initial GPU status file is missing,
the watcher waits only if its exact parent remains live. An exited parent
without status raises; failed terminals, plan/owner changes, live children
and malformed JSON still fail their existing checks. This does not retry a
terminal failure. Five active plans were checked: neither changed source nor
test is directly bound there. All live jobs retain their frozen old copies;
CPU-v3's explicit initial-status preparation remains its actual protection.

The new lifecycle regression fails on the original read with the observed
FileNotFoundError. After the fix,29 focused array/probe/watcher tests pass
in.89s, including live failure and corrupt-status cases. No broader model
test rerun is needed for this queue-only change. Public receipt:
`docs/results/uniform-physics-review-startup-race-regressions-v1.json`, SHA256
`29bf4c8dc9dfae0eec581d7820203540c302be96b5d17baaa488cbe0391eaf01`.

The main controller930391/create1792482701.57 and full427 worker1124805/
create1792495822.32 remain live, with41,862 saved records at11:53:44UTC.
CPU closure, retained references, recovered package watcher and rebound
GPU/CPU queues remain pending behind their exact predecessors. No new
numerical quality value was displayed/interpreted. Training/data/loss/LR,
all quality/detail thresholds and defaults remain unchanged. Full native,
statistical/color/analytic closure and the GPU probe still follow. SOTA,
decisive native superiority and100MP/10s remain unmet/unproven; goal active.
