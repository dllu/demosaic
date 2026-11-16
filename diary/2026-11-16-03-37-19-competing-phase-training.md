# Allocate competing spectral families and launch matched training

Recorded: 2026-11-16T03:37:19-08:00 (America/Los_Angeles).

The lower-noise finite-wire panels are complete. Across the three priors, all
clean targets/cameras/masks agree exactly; 256 lower-noise batch pairs were
checked. This is 1,152 observations of eight sources, not 24 independent scenes.
At the clearest prior, V200 EMA recovers 55.56%/4.84% strong/weak increment near
the edge and 86.74%/8.14% far. The corresponding known-template sensor-pair weak
SNR is 9.37/12.27, an oracle diagnostic rather than unknown-structure detection
power. Shared-edge training still supplies no clear weak-response gain; near-edge
quiet error is slightly worse at this prior. All eight new native comparison
boards were viewed. Original receipts, eight native triplets, the common-display
metadata and source-bootstrap summary are retained in
[the noise-ladder report](../docs/edge-snr-ladder.md).

The next intervention allocates the same eight measured carriers between two
angular families, four slots each, separated by a 20-degree rule. This addresses
the observed tendency to spend the bank on one direction and its harmonics. It
changes neither physical CFA amplitude fits nor the 643-parameter readout. A
second proposal is not a detection; full RAW/parent reuse means its scores are
not independent validation or calibrated confidence.

A closed input-only diagnostic on the existing three caches improves weaker
fundamental proximity within three native DFT bins from 26.56% to 65.63% far and
0% to 18.75% near at the clearest prior. Strong-fundamental proximity falls
67.19% to 62.50% far and 96.88% to 89.06% near. Eight source geometries were used;
CFA/repeat views are not independent sources. These distances are not recovery
bounds or a neural quality result. All 768 CPU selector calls closed before
geometry scoring; six CPU/GPU bridges match exact integer selections. A
principal-Nyquist scorer correction after closure changed zero scored values;
the initial source and receipts remain preserved without replaying selections.

The new `orientation-balanced-cfa-wave` kind uses the same V200 data, seed,
V195 initializer, objective, optimizer and schedule. Admission checks all 197
initial tensors, 393,216 exact four-CFA noisy/ADC channels, zero initial
correction and gradients on exactly four tensors/643 parameters. No admission
optimizer update or probe initializer is used. Existing model kinds keep the
original selector. The review runner now explicitly permits a model intervention
only with unchanged data and initializer; it also uses the correct figure labels.

Training completed after this entry's creation: all 1,000 rows, 900 updates and
100 ADC skips passed the frozen-state/domain audit. Completion checkpoint SHA256
`a15da53b49121ce5587f751c9a75b946a95c8d4958cee564bf1f063d6d4e7492`.
Both raw/EMA endpoints are queued through the complete 822-input suite and all
60 native boards, including both protected GFX families, both cab profiles and
JPEGs. The next worker then evaluates all three immutable fresh-noise caches,
checks the saved V195 anchor exactly, and verifies actual full-forward parity
before using cached contexts for endpoint/gain curves. It performs no new
parent/DINO forwards or source/noise draws. Actual image-quality improvement
remains unmeasured at this observation. No current recommendation changes.
[Prototype, training and exact launch/completion evidence](../docs/competing-wave-candidates.md).

Validation: 42 focused tests pass (selector geometry across four CFAs, existing
component compatibility/checkpoints, matched-review pairing, edge measurements
and native reporting). Ruff passes all changed/new Python entry points. Current
document links resolve, and public compressed receipts decompress to the exact
original SHA256 identities. No historical receipt was rewritten.
