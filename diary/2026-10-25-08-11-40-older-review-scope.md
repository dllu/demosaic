# Scope older correction and native-target reviews

Recorded: 2026-10-25T08:11:40-07:00 (America/Los_Angeles).

Several older guides still described V16 as the current reviewed model or said
that it supplied the README examples. Scope the V18/V19, V20/V21, V22/V23 and
V24/V25 conclusions to their actual parent and training budget, and link current
deployment to `docs/current-model.md`. The usage guide now uses the same selector
instead of naming the superseded V101/V102 family.

Before implementing another broad CFA-residual correction, read the completed
V43 local-mean and V60 flatness-gated probes. The former loses 1.20045dB on eight
development photographs; the latter has negligible photographic change and
mixed noisy-flat errors. Add these existing findings to the research guide.
Scope their rejection language to those operators/checkpoints rather than
implying measurements of current models. No new correction experiment is run.

V118's original child was verified at step17,100/20,000 at 08:11PDT; all17
scheduled validation monitors were finite. Its training controller and all
three original downstream review owners were alive with matching process
creation times. V117 remains complete; trained quality for both arms is pending.

Validation: documentation diff/whitespace and 178 relative-link checks pass;
all41 existing table rows,40 native-image references and15 machine-receipt
references in the nine edited guides are preserved. No production source,
checkpoint, receipt or native crop is changed;
no model inference, noise generation, RAW decode or training is performed here.

