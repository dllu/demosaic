# Queue lower-noise native photo detail views

Recorded: 2026-10-21T18:18:07-07:00 (America/Los_Angeles).

Prepare ADC-only/ISO100 views of the same fixed native photos to examine weak
detail at lower noise. Repeat ISO12800 as a consistency witness. The full
V43/V95/V96/V97 comparison keeps running; no model or primary protocol changes.
Use the first four sources from its immutable427-source manifest as the same
B4 processing packet, retain the same first two sources/ROI for native views,
and preserve all physical calibration, RNG seed, unit exposure and RGGB data.
All four fixed checkpoints and all nine methods remain in each condition.

Implement `scripts/evaluate_v95_native_photo_conditions.py`. Preparation clones
the full suite's frozen numerical package byte-exact:all47 files match.
The16-input/71-file plan pins selected cache/weights, three single-condition
protocols, reference code and licenses. Plan SHA
`603e30d5d46eda4de3665f4eee1aded21d8d7b8c650f60121276034ec71eac6a`.
Runtime must wait for the main controller/worker and all seven stage owners
to exit, verify their completed receipts, then obtain original stable resource
headroom. The full suite stays primary. No new training, checkpoint/source
selection, speed work or output correction is introduced.

Fourteen CPU metadata/control tests pass:calibration/seed/ADC preservation,
independent protocol copies, invalid priors/conditions, dependency plan identity,
all-stage coverage, live-owner release prevention and failed/missing-parent
handling. Ruff and formatting pass. These tests do not run restoration models.
Actual real-protocol comparisons also retain every non-condition setting.

Launch the frozen CPU supervisor once with CUDA hidden. Actual controller
PID3957758/create1792631887.63 waits behind live main evaluation controller
PID3905899/create1792629846.25 and photo worker
PID3906010/create1792629910.88. Observe zero child processes, no worker claim,
no dependency-release evidence and only the artifact-owner marker in its output
namespace. Launch SHA
`d65000bf7a4ef85277eedd25a8a36b3e3e60e7eb828726ae2f51e00df73feeb6`.
At the later observation the main suite advances to192/443 sources while the
diagnostic still waits, with both parent identities revalidated live.

When released, the worker must make12 actual joint/DINO forwards and48 joint
observations across the three conditions, produce36 native triplets, and check
state/DINO/configuration/parameter identity/RNG/physical-input preservation.
The ADC packet must exactly match the full suite's recorded first4-source
input hash. Repeated high-noise noisy/GT pixels must match; a predeclared at-most
one RGB8-code rounding bound checks restored previews, without claiming16-bit
accuracy qualification. Per-condition36-case coverage/arithmetic is checked.
All actual GPU checks and native interpretation remain pending.

Publish the [preparation and observed dependency wait](../docs/results/v95-palette-native-photo-conditions-preparation-v1.json),
SHA `561c81b4093e7f78b8fe64d688deadeb226aafb9b07a91eccfe8e40b2a97d3ac`.
Local plan/code is
`.cache/quality-first-20261020/V95-palette-native-photo-conditions-v1/`;
outputs use
`/mnt/external/demosaic/v95-palette-native-photo-conditions-20261021-v1/`.
No additional quality result or promotion follows from preparation. Keep V43
working reference and speed deferred; the full PROMPT objective remains active.

