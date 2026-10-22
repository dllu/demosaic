# Full-panel ADC sample fidelity checks prepared

Recorded: 2026-10-21T20:58:51-07:00 (America/Los_Angeles).

Prepared full-evaluation ADC fidelity observers while the same V98 production
worker continued. The prior turn made concrete progress: four actual proofs,
an independent checkpoint audit and the bounded production launch. This turn
adds checks that the eventual complete quality panels actually exercise the
physical sample constraint across their full declared coverage.

Only checkpoints explicitly declaring projected inference receive the new
observer. It selects from explicit shot/read profile families, never observed
variance or an ISO label. It measures all valid nonclipped CFA channels in
sensor units without changing prediction/input tensors, model state or RNG.
The 1e-6 sample-error limit is unchanged from the training plan. Empty valid
support yields no maximum; positive-noise paths remain unprojected.

Derived per-model coverage from the frozen evaluation protocol, color cases,
prepared camera manifests and reviewed GFX input conditioning: photo/procedural
1,772; analytic224; color588; known/unseen/GFX/highlights0. Runtime counts must
match before a stage result is written. New metadata lives in a separate
ADC_sample_fidelity field; reference invariant dictionaries and their exact
cross-study gates retain their original schema.

All35 focused tests pass, covering profile selection, coverage counts, false
ISO names, malformed/duplicate CFA grids, extra ADC conditions, nonfinite
priors/observations, empty/clipped support, all-CFA measurement errors, no
tensor/RNG mutation and the existing reference/policy sensitivity gates.
These tests are operator/observer checks, not completed model evaluation.

Replayed the observer on all588 saved final V95 ADC color predictions and
their unchanged observations. All588 raw predictions exceed the same sample
limit; after applying the existing unchanged projection,38,535,168 valid CFA
values have maximum error5.82e-11. All588 positive-noise fields bypass the
operator. No learned model is constructed/forwarded, new noise drawn, threshold
searched or original file changed. Torch RNG stays exact and CUDA hidden.
The [preparation receipt](../docs/results/v95-adc-full-panel-fidelity-preparation-v1.json)
binds the complete replay, archived source/tests and input-derived counts.
This is not a new trained model or RGB16/100MP/quality qualification.

V98 passed1k and2k checkpoint/validation boundaries under the same live owner,
with finite logged training losses/gradients. Eight-source training validation
does not replace the full panels or permit intermediate checkpoint selection.
The original final4k endpoint and common projected V98/V99 comparison remain
primary; V99 runs serially after V98. V43 remains the working reference and
speed work stays deferred.

Final checks pass: 62 static archived references, five local links, Ruff and
whitespace. All 27 training inputs/69 frozen files remain exact. At 21:02 local,
the same V98 owner was live past step2400. Metadata-only CPU loading of the
immutable retained1k/2k files verifies steps1000/2000, original off-policy config
and model/EMA/Adam table sizes71/71/69. This does not replace final independent
finite-state audits and does not select those intermediate endpoints.
