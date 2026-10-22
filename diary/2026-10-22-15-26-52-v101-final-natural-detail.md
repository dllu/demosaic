# V101 completes and improves the selected natural-detail views

Recorded: 2026-10-22T15:26:52-07:00 (America/Los_Angeles).


V101 completed all10,000updates with the planned final EMA. Exact original
workerPID1084785/create1792698707.31 and trainingcontrollerPID844518 both exited
normally. FinalcheckpointSHA256:
`6f691c653a618bdde0d7db501f3efc557a9699e2dbba73cf94c7440b364ef3e3`.
Its initial EMA exactly matched V84 and official frozenDINO hash remained
370a84c2…; V100/V101 share the same frozen numerical-source hash. All four
original discarded smokes and both complete production phases are recorded.
The primary full-quality queue automatically started after both owners exited;
full-frame GFX remains queued behind it. No training was restarted.

The separate CPUF32/two-thread fixed natural-detail reporter completed normally,
using the same12 cached RGGB/ADC-only/ISO100/ISO12800 observations as V84/V100.
V101 improves PSNR/SSIM in all12cases against both; gradient improves12/12 versus
V84 and11/12 versus V100; chroma improves10/12 and9/12 respectively. Four-source
PSNR gains over V84 are+.1548214/+.1099062/+.0167928dB; versus V100,
+.0787010/+.0482368/+.0099640dB. These are selected-context results, not the full427
or real-camera result. V101−V100 tests the combined recipe package, while the
V84 comparison additionally changes budget/optimizer/cohort.

Added12 native160 noisy/restored/exactGT triplets to the current gallery and
actually viewed all72 cells in the three final boards. V101 is highlighted among
the matched checkpoints. Low-noise bark grain/canopy contrast gain slightly;
outputs remain close and high-noise feather/canopy/fur smoothing remains. No
ADC output projection is applied in these training comparisons. Source/ROI,
fullcheckpointSHA/noise/display metadata accompany each native triplet. Shared
noisy/GT pixels and unchanged native-cell hashes pass for every method.

Preserved a self-contained replay of the old V100 galleries before updating,
with boardPNGbytes matching prior viewed images exactly. The new V101 receipt
binds self-contained private copies of all current triplets/manifests/boards.
Original V84/V100 receipts and source crops remain byte-identical; current
gallery paths can advance. One preflight expected `child` in the terminal
status, which omits it; corrected the check to the saved execution record.
Both reporting owners had exited and all endpoint/input/live-plan guards pass.

Updated README and relevant current model/detail/training/requirements/GFX/index
prose to show V101's useful gains and completed status. The broader matched
comparison is running, with unchanged checkpoint/protocol/source snapshots;
its old generic helper's internal running-status string containsV43 but its
actual bound models are V84/V100/V101. Current guides label the actual models.
The full photographic/camera values and GFXfull-frame results await completion.
Broader quality, real-photo superiority, SOTA and100MP10s goals remain open.
