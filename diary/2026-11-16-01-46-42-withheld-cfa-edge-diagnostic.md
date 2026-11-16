# Withheld CFA diagnostic exposes predictable edge leakage

Recorded: 2026-11-16T01:46:42-08:00 (America/Los_Angeles).

Implemented the literature plan's analytic A/B diagnostic while the shared-edge
neural trial trains. Discovery uses only half of each native CFA phase; baseline,
frequency/geometry, amplitudes and plug-in variances exclude the validation
samples. Swapping subsets uses a fixed both-scores threshold rule. A NaN-heldout
test checks this exclusion directly. No parent model or protected photos enter.

After an eight-source pilot, expanded to 64 sources × two independent noise
draws in each of six procedural families, with separate calibration/test seeds,
affine/step nuisance controls and fixed thresholds0–4. All3,072 fit records are
preserved. At threshold2, test flat activations are0/128 in both models, represented
edge activations128/128 versus0/128, and off-grid edge activations128/128 versus
113/128. Step nuisance reduces off-grid false periodic correction from395.97 to
74.28 DN16 and raises near-edge wave projection from3.50% to77.58%, but substantial
off-grid leakage remains. This is restricted analytic evidence, not a model gain
or calibrated confidence. Source-cluster intervals/curve and limitations are in
[the report](../docs/withheld-cfa-evidence.md).

Five diagnostic tests and seven review-pairing tests pass. The actual old V200
60-board render fixture also reproduces8,294,400 RGB channels exactly; reused
fixture pixels supply no shared-edge quality evidence. The review controller
still waits on the exact live original training process. Training/review sources
and existing receipts are unchanged by this CPU diagnostic.

