# Prepare lower-noise native crops for the common ADC comparison

Recorded: 2026-10-21T21:37:44-07:00 (America/Los_Angeles).

V99 continues under its original controller/worker identities. Finite
loss/gradients were observed through step875; the existing CPU handoff queue
remains live and has not released the independent audits or full evaluation.
No additional GPU job or training restart.

Extended `scripts/evaluate_v95_native_photo_conditions.py` to accept both
declared comparisons. V98/V99 requires projected inference on both new
endpoints, final4k lineage from the identical V95 step20k checkpoint and a
distinct retained raw-training checkpoint for the V98 export. V43/V95 retain
their original policies. The older V96/V97 comparison remains unprojected.
Unrelated arms, intermediate steps, initializer changes and nonboolean or
mismatched policy flags fail before model loading.

The native hook observes physical ADC selections using the same read-only
sample-fidelity helper as the full evaluation. It requires4 ADC observations
per projected model in the ADC condition and zero in positive-noise conditions;
valid measured channels must agree within1e-6 sensor units. Positive-noise
conditions cannot silently become zero-prior inputs. Tests cover both shared
and per-observation CFA colors, mixed profile selection, corrupted ADC values
and unchanged inputs/predictions/RNG. These are measured-channel checks, not
unmeasured-color accuracy or RGB16 output qualification.

The unchanged diagnostic uses first4 full-suite sources, fixed fabric/building
native cases, RGGB, IEEEFP32/B4/native256, original ADC/ISO100/ISO12800 priors,
shared physical settings/seeds and no crop resizing. It will produce36 native
triplets only after all7 primary panels and both parent owners finish/exit.
Per-condition core model/input/counter checks persist before optional image
comparisons. No automatic retry or promotion.

Added frozen helper selection for preparation. The prospective archive has74
files including all47 numerical files exact to the training archive. A real
CPU-only preparation using the completed historical V43/V95/V96/V97 parent
copies72 files and16 fixed inputs, including the native and board helpers.
All four actual frozen CLI checks and prospective ADC dependency imports pass.
The historical plan was never launched; its artifact directory contains only
the ownership marker. All69 focused native-policy, crop-board and ADC observer
tests pass in the actual frozen package; Ruff/format/whitespace checks pass.

The [public preparation receipt](../docs/results/v95-adc-native-detail-preparation-v1.json)
has SHA256 `1f17fb3a78b7ecd18934ab07098ebf0f4a9bd9402bd0ca508f3a3a35366dd9e0`.
The new V98/V99 diagnostic is not yet prepared or queued because its full
evaluation parent does not yet exist. No new neural inference, crop output,
visual quality, speed or promotion result is claimed. V43 remains the working
reference; the full goal remains unmet.

