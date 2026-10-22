# Complete matched ADC training and launch full quality evaluation

Recorded: 2026-10-21T22:28:48-07:00 (America/Los_Angeles).

Both matched4k production arms completed under the original controller; the
controller and final worker exited. Each arm records4,000 training/optimizer
updates,128 training-validation forwards and4,128 DINO calls across64,000
training images, including4,751 ADC images. Same initializer, frozen DINO,
numerical package, curated88484 Commons/native128/paired32 recipe and seed58;
the candidate's declared ADC flag is the only effective model-config change.
All161 logged production batches match across every domain, as do each24
discarded CPU/CUDA observations. Final4k remains primary; both validation-best
states are step3000 and stay diagnostic.

Independent CPU saved-state and trace audits pass for both arms: all five
retained model/EMA/Adam states have finite tensors and correct steps/configs,
all161 training observations are finite, all four scheduled eight-source/
28-cell training-validation panels are complete, and each production first24
batch hash matches its own discarded CUDA proof. No inference in these audits.
The earlier read-only midpoint check also found all81 logged batches through2k
identical and69 EMA tensors changed between arms; final audits supersede that
intermediate execution check, which was not a checkpoint-selection exercise.

Final V98 SHA256:
`5e8f5f32bfa3a1f37912566ebac1ca524e0fde1eab616ab215a8795f55ef8d96`.
Final V99 SHA256:
`e74656e5f556c1fa9a6f6655b59f979b89ee3adba7b30cfa08bd5a5a9d6de979`.
V98/V99 independent audit SHA256 values:
`f4c5e333a320bc39a78370f09daac6bc5dd575a84067b0de3847d58a4531cf43` /
`b29efaab6b345c4a233e59dbefa330a6b34c61a66ded604fe54602280f67d57e`.

The original CPU handoff queue completed and exited after preparing/launching
the seven-stage primary evaluator. Its V98 projected export retains exact final
EMA tensors and initializer lineage, verified after serialization; export SHA256
`6d8263f50b26dc6ab9fe18db1bcae6d6714cdbc5985db750e58a00b4e8765a88`.
Primary V99−V98 uses common projected inference, with original V43/V95 policies
as references. No numerical package, corpus, noise/display setting or decision
criterion changed. Primary plan has65 frozen files/1,803 fixed inputs, SHA256
`e657049b99c2f36435f52ceb03b18085b93ccea37a5e0d462f1a311e31515de3`.
Controller PID37769/create1792646420.57 and photo GPU worker
PID37941/create1792646485.63 were confirmed live, with actual score-file growth.

Prepared and launched the lower-noise native diagnostic from the frozen74-file
helper archive. Both actual copied CLIs and ADC-observer dependency imports
pass. Its plan has73 frozen files/16 fixed inputs, SHA256
`5508d4667f3313ac9c2bbe114211c4be49be9737558f045d50fed10680531244`.
CPU controller PID38088/create1792646566.44 waits for all7 primary stages and
exited owners; its GPU worker has not started. It will retain the same first4
sources and fixed fabric/building native160 cases at ADC/ISO100/ISO12800,
with36 triplets and common projected policy. No concurrent secondary inference.

Viewed three already-saved primary ISO12800 native triplets while the full
panel continues: V99 fabric/building (`crop-f1ffca5ecb599f55` /
`crop-c35a0135145fdcdb`) and projected-control V98 fabric
(`crop-0f452518b631009f`). Files are in the primary artifact's `photo/` folder;
adjacent JSONs retain source/checkpoint/ROI/noise/display settings. Both fabric
restorations still soften fine cords and shift color relative to the exact
synthetic GT. The building retains geometry with smoothed sky/cloud detail.
These are isolated fixed examples, not a completed native review or primary
score comparison. No checkpoint selection or promotion follows.

The [completed training and actual launch receipt](../docs/results/v95-adc-training-complete-and-evaluation-launch-v1.json)
has SHA256 `a9b25df8762ccdcfb9b4505d25a83ce6a232dc9662b1de038117f6c3da3d0c8a`.
Full held-out metrics, independent numeric closure, complete native/GFX viewing,
RGB16/full-frame qualification and any promotion decision remain pending.
V43 remains the working reference; the full goal remains unmet. Speed work
stays deferred.

