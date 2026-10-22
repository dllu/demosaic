# Separate ADC and noisy photo contrasts before the V98 V99 review

Recorded: 2026-10-21T21:28:01-07:00 (America/Los_Angeles).

The original V98 worker completed4k and exited. Its retained final checkpoint
has SHA256 `5e8f5f32bfa3a1f37912566ebac1ca524e0fde1eab616ab215a8795f55ef8d96`.
Executed worker counters record4,000 training updates/forwards and128 validation
forwards,4,128 DINO calls. These are worker execution checks; the independent
saved-state audit remains queued. The original controller launched V99 as
PID4168542/create1792643086.75 after its resource wait. Same plan/source/data;
finite loss/gradients observed past step150. The CPU handoff queue is live and
has not released audits or evaluation. No extra GPU job or restart.

Added `scripts/audit_adc_photo_contrasts.py` for the prospective quality
decision. It verifies the complete nine-method,427-photo/16-procedural,
seven-condition/four-CFA score grid and existing summary arithmetic. It then
separates all/explicit ADC/positive shot-or-read priors, retaining source-balanced
PSNR/SSIM means, all paired source deltas, adverse tails and seed42/1,000-resample
source intervals. Photo/procedural sources remain separate. The optional
`--expect-adc-pair` requires projected inference on both new primary endpoints;
it does not substitute for matched-lineage, pixel-metric or visual audits.

All16 focused tests pass in the frozen package, covering misleading condition
labels, independent positive-shot/read selection, a synthetic example where
ADC gains hide a noisy regression, procedural SSIM loss, source rather than
tile resampling, row-order invariance and corrupted/partial grids. Ruff and
formatting pass. The actual CLI rejects the old unprojected pair under the
common-ADC requirement without producing an output.

Rehearsed only on completed V43/V95/V96/V97 saved scores:111,636 rows,48 subset
means and72 contrasts. A separate Decimal50/scalar-bootstrap operator rebuilds
10,632 source-metric means and checks16,428 reported scalar fields, including144
interval endpoints. Maximum difference7.105427357601002e-15. No inference,
noise generation or image decoding. All47 numerical source files remain exact
to the training archive; frozen training/evaluation receipts and history points
are untouched.

The historical V97−V96 photo contrast is +.06118336dB on ADC inputs
[+.03333398,+.09550695], −.00445159dB on positive-noise inputs
[−.02518246,+.01460491], and +.00492483dB overall. This supports inspecting
noise subsets separately; it changes neither the previous stop decision nor
the prospective V98/V99 success criteria. Updated the old review with this
split and corrected a stale statement that its already-reviewed lower-noise
views were still queued.

Preparation plan SHA256:
`fb37f773f43baa7455765e0bb5312754968db552e60767a0107bfbd1178df2ac`.
The [public receipt](../docs/results/v95-adc-photo-contrast-preparation-v1.json)
has SHA256 `2706ac96953acb6764a5ed07a7ba1c2fb1ac8099d942d52faabc63d7a9903d31`.
Actual V98/V99 held-out quality, all remaining diagnostics and native review
are pending. V43 remains the working reference; the full goal is unmet.

